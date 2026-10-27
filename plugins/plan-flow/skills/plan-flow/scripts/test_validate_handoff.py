"""Validator checks, driven by files rendered from the sample specs; no network or product execution."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from render_handoff import render
from validate_handoff import load_directory, validate

SPECS = Path(__file__).resolve().parent.parent / "evals" / "specs"
VALIDATOR = Path(__file__).with_name("validate_handoff.py")


def sample(name):
    return json.loads((SPECS / f"{name}.json").read_text(encoding="utf-8"))


def rendered(name, directory="/work/plans"):
    spec = sample(name)
    issue = spec["issue"].rsplit("/", 1)[1]
    return spec, issue, render(spec, issue, directory)


def check(files, issue, objectives=None, **kwargs):
    errors, warnings, _ = validate(files, issue, objectives, **kwargs)
    return errors, warnings


class ValidatorTests(unittest.TestCase):
    def assertRejects(self, files, issue, fragment, objectives=None, **kwargs):
        errors, _ = check(files, issue, objectives, **kwargs)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_every_sample_layout_passes(self):
        for name in ("compact-bounded", "phased-related-flows", "phased-indivisible",
                     "sensitive-phased", "external-wait", "multi-pr"):
            with self.subTest(name):
                _, issue, files = rendered(name)
                errors, warnings = check(files, issue)
                self.assertEqual((errors, warnings), ([], []))

    def test_objective_count_is_inferred_and_checked(self):
        _, issue, files = rendered("phased-related-flows")
        self.assertEqual(check(files, issue, 3)[0], [])
        self.assertRejects(files, issue, "missing required artifact", objectives=4)
        del files[f"{issue}-exec-obj-2.md"]
        self.assertRejects(files, issue, "exec-obj-2.md: missing required artifact")

    def test_missing_gates_or_ship_blocks(self):
        for suffix in ("gates", "ship"):
            _, issue, files = rendered("phased-indivisible")
            del files[f"{issue}-exec-{suffix}.md"]
            self.assertRejects(files, issue, "missing required artifact")

    def test_compact_and_phased_layouts_cannot_coexist(self):
        _, issue, phased = rendered("phased-indivisible")
        _, _, compact = rendered("compact-bounded")
        stale = {f"{issue}-exec.md": next(iter(compact.values()))}
        self.assertRejects({**phased, **stale}, issue, "conflicting or unrequested artifact")

    def test_stale_canonical_file_is_flagged(self):
        _, issue, files = rendered("compact-bounded")
        files[f"{issue}-implementation-prompt.md"] = "old"
        self.assertRejects(files, issue, "conflicting or unrequested artifact")

    def test_placeholder_blocks_but_helm_text_does_not(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        self.assertRejects({name: files[name].replace("/work/service", "{{workspace}}")}, issue, "unresolved template placeholder")
        self.assertRejects({name: files[name] + "\nTBD\n"}, issue, "unresolved template placeholder")
        helm = files[name].replace("hides caller bugs", 'renders {{ .Values.image }} and {{ include "x" . }}')
        self.assertFalse(any("placeholder" in e for e in check({name: helm}, issue)[0]))

    def test_execution_statement_is_required(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        self.assertRejects({name: files[name].replace("This is an execution prompt.", "A note.")}, issue, "execution-prompt statement")

    def test_header_fields_are_read_from_the_header_only(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        spoof = files[name].replace("Status: ready\n", "") + "\nStatus: ready\n"
        self.assertRejects({name: spoof}, issue, "not marked ready")

    def test_header_field_values_are_validated(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        cases = {
            "Status: ready": ("Status: blocked", "not marked ready"),
            "Compatibility: greenfield": ("Compatibility: maybe", "compatibility mode"),
            "Base: dev@0123abcdef": ("Base: dev", "Base must be"),
            "Issue: https://github.com/example/service/issues/17": ("Issue: https://github.com/example/service/issues/18", "mismatched full issue URL"),
        }
        for original, (changed, fragment) in cases.items():
            with self.subTest(changed):
                self.assertRejects({name: files[name].replace(original, changed)}, issue, fragment)
        self.assertRejects({name: files[name].replace("Planned: ", "Planned: yesterday ", 1)}, issue, "Planned must be")

    def test_cross_file_metadata_must_match(self):
        _, issue, files = rendered("phased-indivisible")
        ship = f"{issue}-exec-ship.md"
        for original, changed, fragment in (
            ("Compatibility: greenfield", "Compatibility: existing", "Compatibility differs"),
            ("Base: dev@0123abcdef", "Base: dev@0123abcdee", "Base differs"),
        ):
            with self.subTest(fragment):
                self.assertRejects({**files, ship: files[ship].replace(original, changed)}, issue, fragment)

    def test_external_wait_must_open_the_file(self):
        _, issue, files = rendered("external-wait")
        name = f"{issue}-exec.md"
        self.assertEqual(check(files, issue)[0], [])
        lines = files[name].splitlines()
        stop = next(line for line in lines if line.startswith("STOP:"))
        late = files[name].replace(stop + "\n", "") + f"\n{stop}\n"
        self.assertRejects({name: late}, issue, "must open the file")
        no_resume = files[name].replace("; resume: exit 0 and a JSON body with status ok", "")
        self.assertRejects({name: no_resume}, issue, "STOP with check: and resume:")

    def test_workspace_needs_absolute_paths(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        relative = files[name].replace("Execution root: /work/service", "Execution root: work/service").replace(
            "Planning files: /work/plans", "Planning files: plans")
        self.assertRejects({name: relative}, issue, "Workspace needs absolute paths")

    def test_validate_pipes_must_keep_failures_visible(self):
        _, issue, files = rendered("phased-indivisible")
        name = f"{issue}-exec-obj-1.md"
        hidden = files[name].replace("set -o pipefail; ", "")
        self.assertRejects({**files, name: hidden}, issue, "pipefail")

    def test_acceptance_ids_must_reach_gates_and_ship(self):
        _, issue, files = rendered("phased-related-flows")
        name = f"{issue}-exec-gates.md"
        self.assertRejects({**files, name: files[name].replace("- AC3 -> objective 3: Device management refuses while frozen\n", "")},
                           issue, "acceptance IDs differ")

    def test_objective_needs_acceptance_ids(self):
        _, issue, files = rendered("phased-indivisible")
        name = f"{issue}-exec-obj-1.md"
        stripped = files[name].replace("- AC1: ", "- ").replace("- AC2: ", "- ")
        self.assertRejects({**files, name: stripped}, issue, "missing acceptance IDs")

    def test_security_controls_must_reach_gates_and_ship_unchanged(self):
        _, issue, files = rendered("sensitive-phased")
        gates, ship = f"{issue}-exec-gates.md", f"{issue}-exec-ship.md"
        self.assertRejects({**files, gates: files[gates].replace("fail closed", "fail open")}, issue, "S1 differs across artifacts")
        self.assertRejects({**files, ship: files[ship].replace("- S2:", "- S9:")}, issue, "missing issue-wide security requirements")

    def test_sensitive_work_needs_completed_review_and_review_line(self):
        _, issue, files = rendered("sensitive-phased")
        gates = f"{issue}-exec-gates.md"
        self.assertRejects({**files, gates: files[gates].replace("Plan review: complete", "Plan review: unavailable")}, issue,
                           "plan review status")
        no_line = "\n".join(line for line in files[gates].splitlines() if not line.startswith("Review:"))
        self.assertRejects({**files, gates: no_line}, issue, "Review: line")

    def test_sensitive_flag_forces_review_even_if_files_say_no(self):
        _, issue, files = rendered("compact-bounded")
        self.assertRejects(files, issue, "sensitive work needs an explicit completed plan review", sensitive=True)

    def test_pr_rows_cover_each_objective_exactly_once(self):
        _, issue, files = rendered("multi-pr")
        ship = f"{issue}-exec-ship.md"
        self.assertEqual(check(files, issue)[0], [])
        twice = files[ship].replace("objectives=3; keyword=Closes", "objectives=2,3; keyword=Closes")
        self.assertRejects({**files, ship: twice}, issue, "objective 2 must appear in exactly one PR row")
        none = files[ship].replace("objectives=1,2; keyword=Refs", "objectives=1; keyword=Refs")
        self.assertRejects({**files, ship: none}, issue, "objective 2 must appear in exactly one PR row")
        two_closes = files[ship].replace("keyword=Refs", "keyword=Closes")
        self.assertRejects({**files, ship: two_closes}, issue, "exactly one PR row must use keyword=Closes")
        rows = "\n".join(line for line in files[ship].splitlines() if not line.startswith("- PR"))
        self.assertRejects({**files, ship: rows}, issue, "no PR rows")

    def test_oversized_file_warns_but_passes(self):
        _, issue, files = rendered("compact-bounded")
        name = f"{issue}-exec.md"
        padded = files[name].replace("Dirty paths: none", "Dirty paths: " + "x" * 14000)
        errors, warnings = check({name: padded}, issue)
        self.assertEqual(errors, [])
        self.assertTrue(any("over the" in w for w in warnings), warnings)

    def test_unreadable_artifact_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "17-exec.md").write_bytes(b"\xff\xfe\x00bad")
            files, read_errors = load_directory(Path(temp), "17")
            self.assertTrue(any("cannot read artifact" in e for e in read_errors))
            self.assertEqual(files, {})


class CommandLineTests(unittest.TestCase):
    def run_cli(self, directory, *args):
        return subprocess.run([sys.executable, str(VALIDATOR), "--directory", str(directory), "--issue", "17", *args],
                              capture_output=True, text=True, check=False)

    def test_cli_reports_ok_for_valid_directory_and_never_modifies_files(self):
        _, _, files = rendered("compact-bounded")
        with tempfile.TemporaryDirectory() as temp:
            for name, text in files.items():
                (Path(temp) / name).write_text(text, encoding="utf-8")
            before = {p.name: p.read_bytes() for p in Path(temp).iterdir()}
            result = self.run_cli(temp)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["ok"])
            self.assertIn("17-exec.md", report["files"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in Path(temp).iterdir()})

    def test_cli_fails_for_empty_directory_and_bad_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.run_cli(temp).returncode, 1)
            self.assertEqual(self.run_cli(temp, "--objectives", "0").returncode, 2)


if __name__ == "__main__":
    unittest.main()
