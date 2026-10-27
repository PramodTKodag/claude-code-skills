"""Decision lookup checks against throwaway repositories; nothing outside the temp directory is touched."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from decisions_lookup import FILE_RE, TOP_FIRST, key_of, parse_decision, resolve, split_ref

LOOKUP = Path(__file__).with_name("decisions_lookup.py")
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "protocol.file.allow=always"]
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}

README = """\
| Decision | Summary | Status |
|---|---|---|
| [0001](./0001-queue-ordering.md) | Partition ordering guarantees for zebra events | Accepted |
| [0002](./0002-legacy-llama-routing.md) | Old routing | Superseded |
| [0003](./0003-provider-neutral-llama-routing.md) | New routing | Accepted |
| [0009](./0009-ghost.md) | Row whose file was deleted | Accepted |
"""


def git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, env=ENV)


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def adr(number, title, status, decision=""):
    return f"# {number}. {title}\n\n## Status\n\n{status}\n\n## Context\n\nc\n\n## Decision\n\n{decision}\n"


def commit_all(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")


def seed_register(seed, filler=10):
    write(seed, "docs/decisions/README.md", README)
    write(seed, "docs/decisions/0001-queue-ordering.md", adr(1, "Queue ordering", "Accepted"))
    write(seed, "docs/decisions/0002-legacy-llama-routing.md", adr(2, "Legacy llama routing", "Superseded by [0003](0003-provider-neutral-llama-routing.md)"))
    write(seed, "docs/decisions/0003-provider-neutral-llama-routing.md", adr(3, "Provider neutral llama routing", "Accepted"))
    write(seed, "docs/decisions/0004-giraffe-telemetry-export.md", adr(4, "Giraffe telemetry export", "Proposed"))
    write(seed, "docs/decisions/0005-okapi-retry-budget.md", adr(5, "Okapi retry budget", "Deprecated"))
    write(seed, "docs/decisions/0010-orphan-file.md", adr(10, "Orphan file", "Accepted"))
    for n in range(filler):
        write(seed, f"docs/decisions/{100 + n:04d}-filler.md", adr(100 + n, f"Filler topic{n}", "Accepted"))


def make_service(root, filler=10):
    """(seed clone that plays the remote's writer, service clone that may go stale)."""
    remote, seed, service = root / "remote.git", root / "seed", root / "service"
    subprocess.run([*GIT, "init", "--bare", "-q", "-b", "main", str(remote)], check=True, capture_output=True, env=ENV)
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    seed_register(seed, filler)
    commit_all(seed)
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-q", "-u", "origin", "main")
    subprocess.run([*GIT, "clone", "-q", str(remote), str(service)], check=True, capture_output=True, env=ENV)
    return seed, service


def make_sibling(root):
    """A second checkout with an ADR-prefixed register and no remote."""
    sibling = root / "platform"
    sibling.mkdir()
    git(sibling, "init", "-q", "-b", "main")
    write(sibling, "docs/adr/ADR-0001-llama-retry-budget.md", adr(1, "Llama retry budget", "Accepted"))
    commit_all(sibling)
    return sibling


def lookup(cwd, terms, *flags, fetch=False):
    argv = [sys.executable, str(LOOKUP), *([] if fetch else ["--no-fetch"]), *flags]
    done = subprocess.run(argv, cwd=cwd, input=terms, capture_output=True, text=True, check=False, env=ENV)
    assert done.returncode == 0, done.stderr
    return done.stdout


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.seed, self.service = make_service(self.root)

    def test_auto_detects_the_usual_register_and_reads_the_remote_default(self):
        out = lookup(self.service, "queue ordering zebra")
        self.assertIn("registers from auto-detected directories", out)
        self.assertIn("Tier 1 - docs/decisions", out)
        self.assertIn("0001 [Accepted] Queue ordering | docs/decisions/0001-queue-ordering.md", out)
        self.assertIn("origin/main@", out)
        self.assertIn("(fetch skipped)", out)

    def test_superseded_record_points_at_its_replacement(self):
        out = lookup(self.service, "legacy")
        self.assertIn("0002 [Superseded -> 0003]", out)
        self.assertIn("0003 [Accepted]", out)
        self.assertIn("(replaces 0002)", out)

    def test_unsettled_and_retired_statuses_are_labelled(self):
        self.assertIn("0004 [Proposed]", lookup(self.service, "giraffe telemetry export"))
        self.assertIn("0005 [Deprecated]", lookup(self.service, "okapi retry budget"))

    def test_readme_and_file_mismatches_are_reported(self):
        out = lookup(self.service, "zebra queue ordering")
        self.assertIn("0009-ghost.md listed in docs/decisions/README.md but no file", out)
        self.assertIn("0010-orphan-file.md has no docs/decisions/README.md row", out)

    def test_fetch_reads_latest_origin_instead_of_a_stale_checkout(self):
        (self.seed / "docs/decisions/0004-giraffe-telemetry-export.md").unlink()
        write(self.seed, "docs/decisions/0020-capybara-quota.md", adr(20, "Capybara quota", "Accepted"))
        commit_all(self.seed)
        git(self.seed, "push", "-q", "origin", "main")
        out = lookup(self.service, "capybara quota giraffe telemetry", fetch=True)
        self.assertIn("0020 [Accepted]", out)
        self.assertNotIn("0004", out)
        self.assertIn("(fetched)", out)
        self.assertIn("working tree differs from origin/main in 2 file(s)", out)

    def test_explicit_ref_pins_the_read(self):
        write(self.service, "docs/decisions/0030-ostrich-cache.md", adr(30, "Ostrich cache", "Accepted"))
        commit_all(self.service)
        self.assertNotIn("0030", lookup(self.service, "ostrich cache"))
        self.assertIn("0030 [Accepted]", lookup(self.service, "ostrich cache", "--register", "docs/decisions@HEAD"))

    def test_unknown_or_option_like_ref_falls_back_to_the_working_tree_and_says_so(self):
        for ref in ("no-such-ref", "--output=x"):
            with self.subTest(ref=ref):
                out = lookup(self.service, "queue ordering", "--register", f"docs/decisions@{ref}")
                self.assertIn(f"working tree (ref {ref} not found)", out)
                self.assertIn("0001 [Accepted]", out)

    def test_register_flags_order_tiers_across_checkouts(self):
        sibling = make_sibling(self.root)
        out = lookup(self.service, "llama retry routing", "--register", str(sibling / "docs/adr"), "--register", "docs/decisions")
        order = [out.index(marker) for marker in ("Tier 1", "ADR-0001", "Tier 2", "0003 [Accepted]")]
        self.assertEqual(order, sorted(order))
        self.assertIn("working tree (no origin ref)", out)

    def test_profile_decisions_section_configures_registers_and_flags_override_it(self):
        sibling = make_sibling(self.root)
        write(self.service, ".claude/dev-flow-context.md",
              f"# Profile\n\n## Decisions\n\n- Platform: `{sibling / 'docs/adr'}`\n- Own: `docs/decisions@origin/main`\n\n## Other\n\n- `ignored/path`\n")
        out = lookup(self.service, "llama retry routing")
        self.assertIn("registers from profile `## Decisions`", out)
        self.assertLess(out.index("ADR-0001"), out.index("0003 [Accepted]"))
        self.assertNotIn("ignored/path", out)
        flagged = lookup(self.service, "llama retry routing", "--register", "docs/decisions")
        self.assertIn("registers from --register flags", flagged)
        self.assertNotIn("ADR-0001", flagged)

    def test_register_outside_any_checkout_is_a_stated_gap(self):
        loose = self.root / "loose"
        loose.mkdir()
        out = lookup(self.service, "queue ordering", "--register", str(loose / "adr"))
        self.assertIn("UNAVAILABLE", out)
        self.assertIn("not inside a git checkout", out)

    def test_no_register_is_a_stated_gap(self):
        bare = self.root / "bare"
        bare.mkdir()
        git(bare, "init", "-q", "-b", "main")
        out = lookup(bare, "queue ordering")
        self.assertIn("no decision register configured or found", out)
        self.assertIn("do not claim decision coverage", out)

    def test_no_terms_asks_for_terms(self):
        self.assertIn("no terms on stdin", lookup(self.service, ""))

    def test_output_is_capped(self):
        for n in range(TOP_FIRST + 8):
            write(self.service, f"docs/decisions/{200 + n:04d}-quokka.md", adr(200 + n, f"Quokka policy{n}", "Accepted"))
        commit_all(self.service)
        git(self.service, "push", "-q", "origin", "HEAD:main")
        out = lookup(self.service, "quokka", fetch=True)
        self.assertEqual(out.count("  - 02"), TOP_FIRST)

    def test_lexical_only_caveat_is_always_printed(self):
        self.assertIn("absence of a hit is not proof", lookup(self.service, "zzzunmatched"))


class ParsingTests(unittest.TestCase):
    def test_file_names_across_register_conventions(self):
        cases = {
            "0007-use-postgres.md": "0007",
            "ADR-0007-use-postgres.md": "ADR-0007",
            "adr-007-use-postgres.md": "adr-007",
            "SVC-billing-0001-retry.md": "SVC-billing-0001",
        }
        for name, ident in cases.items():
            with self.subTest(name=name):
                self.assertEqual(FILE_RE.match(name).group(1), ident)
        for name in ("README.md", "template.md", "index.md"):
            self.assertIsNone(FILE_RE.match(name))

    def test_identifiers_compare_by_prefix_and_number(self):
        self.assertEqual(key_of("ADR-0007"), ("adr", 7))
        self.assertEqual(key_of("0007"), ("", 7))

    def test_reference_resolves_to_the_only_decision_with_that_number(self):
        pool = [parse_decision("0007", "s", "p.md", "# 7. T\n\n## Status\n\nAccepted\n")]
        self.assertIs(resolve("ADR-0007", pool), pool[0])
        self.assertIsNone(resolve("ADR-0008", pool))

    def test_split_ref(self):
        self.assertEqual(split_ref("docs/adr@origin/main"), ("docs/adr", "origin/main"))
        self.assertEqual(split_ref("docs/adr"), ("docs/adr", ""))

    def test_status_styles(self):
        cases = {
            "## Status\n\n**Superseded by [ADR-0043](./a.md)** — kept\n": ("Superseded", "ADR-0043"),
            "## Status\n\nSuperseded by [the new routing](0012-new-routing.md)\n": ("Superseded", "0012"),
            "Status: Accepted\n": ("Accepted", ""),
            "- **Status:** Accepted (design). Implementation deferred\n": ("Accepted", ""),
            "## Status\n\nRejected\n": ("Rejected", ""),
            "## Status\n\nCouncil-deferred (5/5)\n": ("Unrecognized", ""),
            "---\nstatus: \"accepted\"\n---\n\nbody\n": ("Accepted", ""),
        }
        for text, (status, replaced_by) in cases.items():
            with self.subTest(text=text):
                decision = parse_decision("ADR-0001", "slug", "p.md", f"# ADR-0001: Title\n\n{text}")
                self.assertEqual((decision.status, decision.replaced_by), (status, replaced_by))

    def test_status_block_references_name_related_decisions(self):
        text = "# ADR-0038: T\n\n## Status\n\nAccepted, amended by [ADR-0044](./r.md).\n"
        self.assertIn("ADR-0044", parse_decision("ADR-0038", "s", "p.md", text).status_refs)

    def test_title_drops_the_identifier_prefix(self):
        cases = {
            "# ADR-0001: A title": "A title",
            "# ADR-0001 — A title": "A title",
            "# 1. A title": "A title",
            "# A plain title": "A plain title",
        }
        for heading, title in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(parse_decision("ADR-0001", "s", "p.md", f"{heading}\n\nStatus: Accepted\n").title, title)


if __name__ == "__main__":
    unittest.main()
