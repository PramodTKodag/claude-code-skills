"""Live decision lookup for planning, printed as short lines.

Reads the repo's own `decisions/` folder (ADR-style files) from its default branch, fetched first so the
latest accepted decisions are seen. Only the anchor repo is read: no other repo, path or profile setting
can add a register. Nothing is cached or hardcoded: the decision files are the source of truth, README
tables only supply summary text.

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

from preflight import capped, git, run

REGISTER = "decisions"
ORIGIN_FALLBACKS = ("origin/main", "origin/master", "origin/dev", "origin/trunk")
FETCH_TIMEOUT = 30
READ_TIMEOUT = 8
MAX_READ = 12000
TOP_CANDIDATES = 10
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


def open_source(root, do_fetch):
    """(Source, how it was read): fetches first, then reads the default branch, else the working tree."""
    fetched = do_fetch and fetch(root)
    state = "fetched" if fetched else "fetch skipped" if not do_fetch else "fetch failed, last known"
    ref = next((r for r in default_refs(root) if verified(root, r)), None)
    if ref is None:
        return Source(root, None), "working tree (no origin ref)"
    return Source(root, ref), f"{ref}@{git(root, 'rev-parse', '--short', ref)} ({state})"


def section(text, name):
    found = re.search(rf"^##\s+{name}\s*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return found.group(1) if found else ""


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


def report_register(root, terms, do_fetch):
    """Print the repo's decision candidates; returns the coverage lines."""
    source, how = open_source(root, do_fetch)
    decisions, indexed = scan_register(source, REGISTER)
    print(f"Repo decisions - {REGISTER}/ (Accepted binds; Proposed/Unrecognized is unsettled: ask if design depends on it; "
          "Superseded/Deprecated/Rejected do not bind)")
    if not decisions:
        print("  (no decision files found)")
        return [f"{REGISTER}/ read at {how}: no decision files; state this gap, do not claim decision coverage"]
    print_decisions(decisions, terms, TOP_CANDIDATES)
    counts = Counter(d.status for d in decisions)
    coverage = [f"{REGISTER}/ read at {how}: {len(decisions)} scanned (" + ", ".join(f"{s} {n}" for s, n in sorted(counts.items())) + ")"]
    if source.ref:
        changed = set((git(root, "diff", "--name-only", source.ref, "--", REGISTER) or "").splitlines())
        changed |= set((git(root, "diff", "--name-only", "HEAD", source.ref, "--", REGISTER) or "").splitlines())
        if changed:
            coverage.append(f"{REGISTER}/ working tree differs from {source.ref} in {len(changed)} file(s); "
                            f"{source.ref} was read, so open files with `git show {source.ref}:<path>`")
    if indexed:
        files = {Path(d.path).name for d in decisions}
        coverage += capped([f"{name} listed in {REGISTER}/README.md but no file" for name in sorted(indexed - files)
                            if FILE_RE.match(name)] +
                           [f"{name} has no {REGISTER}/README.md row" for name in sorted(files - indexed)], "README mismatches")
    return coverage


def main():
    parser = argparse.ArgumentParser(description="Live decision lookup of the repo's decisions/ folder; terms on stdin.")
    parser.add_argument("--no-fetch", action="store_true", help="skip git fetch (offline)")
    args = parser.parse_args()
    terms = sorted(words("" if sys.stdin.isatty() else sys.stdin.read()))
    if not terms:
        print("decisions lookup: no terms on stdin; pass 5-12 behavior terms and touched paths")
        return 0
    root = git(Path.cwd(), "rev-parse", "--show-toplevel")
    print("decisions lookup (lexical candidates from titles and README summaries; verify each Status and Decision)")
    if root:
        coverage = report_register(Path(root), terms, not args.no_fetch)
    else:
        print("  (cwd is not inside a git repository)")
        coverage = ["no repository: no decisions were read; do not claim decision coverage"]
    coverage.append("lexical match only, so absence of a hit is not proof that no decision applies")
    for line in coverage:
        print(f"coverage: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
