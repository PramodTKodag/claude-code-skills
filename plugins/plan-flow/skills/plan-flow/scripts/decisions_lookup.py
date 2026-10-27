"""Live decision lookup for planning, printed as short lines.

Reads architecture-decision registers (ADR-style directories) at a pinned git ref, fetched first so the
latest accepted decisions are seen. Nothing is cached or hardcoded: the decision files are the source of
truth, README tables only supply summary text. Registers come from, in order of precedence:
  1. --register PATH[@REF] flags (repeatable; the first binds first),
  2. the `## Decisions` section of the repo profile (.agents/ or .claude/dev-flow-context.md),
  3. auto-detection among the usual directories (docs/decisions, docs/adr, adr, ...).
A relative PATH is relative to the anchor repo; PATH may point into another checkout. PATH cannot contain `@`.

Terms (behavior words, touched paths) arrive on stdin so no issue text reaches a shell. The only write
is `git fetch`. The output is a lexical candidate list, never proof that no other decision applies.
"""

import argparse
from collections import Counter
from dataclasses import dataclass, field
import math
from pathlib import Path
import re
import subprocess
import sys

from preflight import PROFILE_PATHS, capped, git, run

DEFAULT_REGISTERS = ("docs/decisions", "docs/adr", "docs/adrs", "docs/architecture/decisions",
                     "adr", "adrs", "decisions", "doc/adr", "doc/arch")
ORIGIN_FALLBACKS = ("origin/main", "origin/master", "origin/dev", "origin/trunk")
FETCH_TIMEOUT = 30
READ_TIMEOUT = 8
MAX_READ = 12000
TOP_FIRST = 10
TOP_LATER = 6
MAX_RELATED = 6
MIN_SCORE = 1.0
RELATIVE_FLOOR = 0.25
TITLE_WEIGHT, SUMMARY_WEIGHT = 2, 1

PREFIX = r"(?:[A-Za-z][A-Za-z0-9]*-)"
FILE_RE = re.compile(rf"^({PREFIX}*?\d{{2,5}})-(.+)\.md$")
ID_RE = re.compile(rf"\b({PREFIX}+\d{{2,5}})\b")
ROW_RE = re.compile(r"^\|\s*\[[^\]]*\]\(([^)#\s]+\.md)[^)]*\)\s*\|\s*(.*?)\s*\|", re.M)
STATUS_RE = re.compile(rf"\b(Proposed|Accepted|Deprecated|Rejected|Superseded)\b(?:\s+by\s+\[?({PREFIX}*\d{{2,5}}))?", re.I)
LINK_TARGET_RE = re.compile(r"\]\(([^)#\s]+\.md)")
STATUS_ORDER = {"Accepted": 0, "Proposed": 1, "Unrecognized": 2, "Deprecated": 3, "Rejected": 3, "Superseded": 3}


@dataclass
class Decision:
    ident: str
    path: str
    title: str
    status: str
    replaced_by: str = ""
    status_refs: set = field(default_factory=set)
    summary: str = ""


def key_of(ident):
    """(lowercased prefix, number): `ADR-0007`, `adr-7` and `0007` name the same number in one register."""
    found = re.fullmatch(r"(.*?)-?(\d+)", ident)
    return (found.group(1).lower(), int(found.group(2))) if found else (ident.lower(), -1)


class Source:
    """Files of one checkout read at a pinned ref, or from the working tree when no ref exists."""

    def __init__(self, root, ref):
        self.root = Path(root)
        self.ref = ref

    def names(self, directory):
        if self.ref:
            listing = git(self.root, "ls-tree", "--name-only", self.ref, f"{directory}/")
            return [Path(line).name for line in (listing or "").splitlines()]
        folder = self.root / directory
        return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []

    def read(self, path, limit=MAX_READ):
        if self.ref:
            command = ["git", "--no-optional-locks", "show", f"{self.ref}:{path}"]
            try:
                done = subprocess.run(command, cwd=self.root, capture_output=True, timeout=READ_TIMEOUT, check=False)
            except (OSError, subprocess.TimeoutExpired):
                return None
            data = done.stdout if done.returncode == 0 else None
        else:
            try:
                data = (self.root / path).read_bytes()
            except OSError:
                data = None
        if data is None:
            return None
        text = data.decode("utf-8", errors="replace")
        return text[:limit] if limit else text


def verified(root, ref):
    return bool(ref) and not ref.startswith("-") and bool(git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"))


def default_refs(root):
    origin_head = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    return ([origin_head] if origin_head else []) + list(ORIGIN_FALLBACKS)


def fetch(root):
    command = ["git", "--no-optional-locks", "fetch", "--quiet", "--no-tags", "--recurse-submodules=no", "origin"]
    return run(command, root, timeout=FETCH_TIMEOUT) is not None


class Checkouts:
    """Opens each checkout once: one fetch per checkout however many registers it holds."""

    def __init__(self, do_fetch):
        self.do_fetch = do_fetch
        self.fetched = {}

    def fetch_state(self, root):
        if not self.do_fetch:
            return "fetch skipped"
        if root not in self.fetched:
            self.fetched[root] = fetch(root)
        return "fetched" if self.fetched[root] else "fetch failed, last known"

    def open(self, root, explicit_ref):
        state = self.fetch_state(root)
        if explicit_ref and not verified(root, explicit_ref):
            return Source(root, None), f"working tree (ref {explicit_ref} not found)"
        ref = explicit_ref or next((r for r in default_refs(root) if verified(root, r)), None)
        if ref is None:
            return Source(root, None), "working tree (no origin ref)"
        return Source(root, ref), f"{ref}@{git(root, 'rev-parse', '--short', ref)} ({state})"


def split_ref(token):
    path, at, ref = token.partition("@")
    return (path.strip(), ref.strip() if at else "")


def section(text, name):
    found = re.search(rf"^##\s+{name}\s*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return found.group(1) if found else ""


def profile_registers(top):
    """Backticked `path[@ref]` tokens from the profile's `## Decisions` section, in listed order."""
    for relative in PROFILE_PATHS:
        profile = Path(top) / relative
        if profile.is_file():
            body = section(profile.read_text(encoding="utf-8", errors="replace"), "Decisions")
            return [split_ref(token) for token in re.findall(r"`([^`\n]+)`", body)]
    return []


def locate(base, path):
    """(checkout root, path inside it) for a register path, or (None, path) outside any git checkout."""
    target = Path(path).expanduser()
    target = (target if target.is_absolute() else Path(base) / target).resolve()
    probe = target
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    root = git(probe, "rev-parse", "--show-toplevel")
    if not root:
        return None, path
    try:
        return Path(root).resolve(), target.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return None, path


def status_block(text):
    block = section(text, "Status")
    if block.strip():
        return block.strip()
    front = re.match(r"---\n(.*?)\n---", text, re.S)
    if front:
        found = re.search(r"^status:\s*(.+)$", front.group(1), re.M | re.I)
        if found:
            return found.group(1).strip().strip("\"'")
    inline = re.search(r"^[-*\s]*\**Status\**\s*:\s*\**\s*(.+)$", text, re.M | re.I)
    return inline.group(1).strip() if inline else ""


def parse_decision(ident, slug, path, text):
    heading = re.search(r"^#\s+(.+)$", text, re.M)
    title = re.sub(rf"^(?:{PREFIX}*\d+)[.:)\s—–-]+", "", heading.group(1).strip()) if heading else slug
    block = status_block(text)
    first = block.splitlines()[0] if block else ""
    found = STATUS_RE.search(first)
    status = found.group(1).capitalize() if found else "Unrecognized"
    replaced_by = ""
    if found and status == "Superseded":
        link = LINK_TARGET_RE.search(first)
        linked = FILE_RE.match(Path(link.group(1)).name) if link else None
        replaced_by = found.group(2) or (linked.group(1) if linked else "")
    return Decision(ident, path, title or slug, status, replaced_by, set(ID_RE.findall(block)) - {ident})


def scan_register(source, register):
    """(decisions, README-listed file names, README has rows); the files, not the README, define what exists."""
    decisions = []
    for name in source.names(register):
        match = FILE_RE.match(name)
        text = source.read(f"{register}/{name}") if match else None
        if text is not None:
            decisions.append(parse_decision(match.group(1), match.group(2), f"{register}/{name}", text))
    rows = {Path(target).name: summary for target, summary in ROW_RE.findall(source.read(f"{register}/README.md", limit=None) or "")}
    for decision in decisions:
        decision.summary = rows.get(Path(decision.path).name, "")
    return decisions, set(rows)


def words(text):
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def matches(term, vocabulary):
    return term in vocabulary or (len(term) >= 5 and any(len(w) >= 5 and w[:5] == term[:5] for w in vocabulary))


def rank(items, terms, limit):
    """Rank (head, body, payload) items by rarity-weighted term hits: head words count double, common terms count little."""
    scored = [(words(head), words(body), payload) for head, body, payload in items]
    total = len(scored)
    weight = {}
    for term in terms:
        seen = sum(1 for head, body, _ in scored if matches(term, head) or matches(term, body))
        weight[term] = math.log(1 + total / seen) if seen else 0.0
    ranked = []
    for head, body, payload in scored:
        score = sum(weight[t] * (TITLE_WEIGHT if matches(t, head) else SUMMARY_WEIGHT if matches(t, body) else 0)
                    for t in terms)
        ranked.append((score, payload))
    ranked.sort(key=lambda pair: (-pair[0], STATUS_ORDER.get(pair[1].status, 0), pair[1].path))
    floor = max(MIN_SCORE, RELATIVE_FLOOR * ranked[0][0]) if ranked else MIN_SCORE
    return [payload for score, payload in ranked[:limit] if score >= floor]


def rank_decisions(decisions, terms, limit):
    return rank([(f"{d.title} {Path(d.path).name}", d.summary, d) for d in decisions], terms, limit)


def resolve(ident, pool):
    """Decision a reference names: same prefix and number, else the only decision with that number."""
    wanted = key_of(ident)
    exact = [d for d in pool if key_of(d.ident) == wanted]
    if exact:
        return exact[0]
    same_number = [d for d in pool if key_of(d.ident)[1] == wanted[1]]
    return same_number[0] if len(same_number) == 1 else None


def related(selected, pool):
    """Decisions the selection depends on: replacements of superseded records and records its status block names."""
    chosen = {key_of(d.ident) for d in selected}
    extra = []

    def add(found, note):
        if found and key_of(found.ident) not in chosen:
            chosen.add(key_of(found.ident))
            extra.append((found, note))

    for decision in selected:
        if decision.replaced_by:
            add(resolve(decision.replaced_by, pool), f"replaces {decision.ident}")
        for ref in sorted(decision.status_refs):
            add(resolve(ref, pool), f"named in {decision.ident} status")
    return extra[:MAX_RELATED]


def decision_line(decision, note=""):
    status = decision.status + (f" -> {decision.replaced_by}" if decision.replaced_by else "")
    suffix = f"  ({note})" if note else ""
    return f"  - {decision.ident} [{status}] {decision.title[:90]} | {decision.path}{suffix}"


def print_decisions(decisions, terms, limit):
    top = rank_decisions(decisions, terms, limit)
    for decision in top:
        print(decision_line(decision))
    for decision, note in related(top, decisions):
        print(decision_line(decision, note))
    if not top:
        print("  (no candidate matched the terms)")


def report_register(tier, spec, checkouts, anchor, terms):
    """Print one register's candidates; returns its coverage lines."""
    path, explicit_ref = spec
    root, inside = locate(anchor, path)
    heading = f"Tier {tier} - {path}"
    if root is None:
        print(f"{heading}: UNAVAILABLE")
        return [f"{path} is not inside a git checkout; read it by hand and state this gap"]
    source, how = checkouts.open(root, explicit_ref)
    decisions, indexed = scan_register(source, inside)
    note = "binds before later tiers; " if tier == 1 else "refines earlier tiers; must not contradict them; "
    print(f"{heading} ({note}Accepted binds; Proposed/Unrecognized is unsettled: ask if design depends on it; "
          "Superseded/Deprecated/Rejected do not bind)")
    if not decisions:
        print("  (no decision files found)")
        return [f"{path} (checkout {root}) read at {how}: no decision files"]
    print_decisions(decisions, terms, TOP_FIRST if tier == 1 else TOP_LATER)
    counts = Counter(d.status for d in decisions)
    coverage = [f"{path} (checkout {root}) read at {how}: {len(decisions)} scanned (" +
                ", ".join(f"{s} {n}" for s, n in sorted(counts.items())) + ")"]
    if source.ref:
        changed = set((git(root, "diff", "--name-only", source.ref, "--", inside) or "").splitlines())
        changed |= set((git(root, "diff", "--name-only", "HEAD", source.ref, "--", inside) or "").splitlines())
        if changed:
            coverage.append(f"{path} working tree differs from {source.ref} in {len(changed)} file(s); "
                            f"{source.ref} was read, so open files with `git -C {root} show {source.ref}:<path>`")
    if indexed:
        files = {Path(d.path).name for d in decisions}
        coverage += capped([f"{name} listed in {path}/README.md but no file" for name in sorted(indexed - files)
                            if FILE_RE.match(name)] +
                           [f"{name} has no {path}/README.md row" for name in sorted(files - indexed)], "README mismatches")
    return coverage


def detect_registers(anchor, checkouts):
    """Usual register directories that hold at least one decision file in the anchor repo."""
    source, _ = checkouts.open(Path(anchor), None)
    return [(path, "") for path in DEFAULT_REGISTERS if any(FILE_RE.match(n) for n in source.names(path))]


def main():
    parser = argparse.ArgumentParser(description="Live decision lookup; terms on stdin.")
    parser.add_argument("--register", action="append", default=[], metavar="PATH[@REF]",
                        help="decision register directory; repeat for several, earlier binds first")
    parser.add_argument("--no-fetch", action="store_true", help="skip git fetch (offline)")
    args = parser.parse_args()
    terms = sorted(words("" if sys.stdin.isatty() else sys.stdin.read()))
    if not terms:
        print("decisions lookup: no terms on stdin; pass 5-12 behavior terms and touched paths")
        return 0
    cwd = Path.cwd()
    top = git(cwd, "rev-parse", "--show-toplevel")
    anchor = top or str(cwd)
    checkouts = Checkouts(not args.no_fetch)
    registers = [split_ref(token) for token in args.register]
    origin = "--register flags"
    if not registers and top:
        registers, origin = profile_registers(top), "profile `## Decisions`"
    if not registers and top:
        registers, origin = detect_registers(top, checkouts), "auto-detected directories"
    print(f"decisions lookup (lexical candidates from titles and README summaries; verify each Status and Decision); registers from {origin}")
    coverage = []
    for tier, spec in enumerate(registers, start=1):
        coverage += report_register(tier, spec, checkouts, anchor, terms)
    if not registers:
        print("  (no decision register configured or found)")
        coverage.append("no register: add a `## Decisions` section to the profile or pass --register; do not claim decision coverage")
    coverage.append("lexical match only, so absence of a hit is not proof that no decision applies")
    for line in coverage:
        print(f"coverage: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
