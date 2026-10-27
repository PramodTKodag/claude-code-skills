"""Renderer checks: spec validation, routing of facts per file, token discipline, write safety."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from handoff_common import TOKEN_BUDGET, est_tokens
from render_handoff import PHASE_RULE, RULES, check_spec, render, run

SPECS = Path(__file__).resolve().parent.parent / "evals" / "specs"
RENDERER = Path(__file__).with_name("render_handoff.py")


def sample(name):
    return json.loads((SPECS / f"{name}.json").read_text(encoding="utf-8"))


def files_for(name, directory="/work/plans"):
    spec = sample(name)
    return spec, render(spec, spec["issue"].rsplit("/", 1)[1], directory)


class SpecChecks(unittest.TestCase):
    def assertSpecRejected(self, mutate, fragment, name="phased-related-flows"):
        spec = sample(name)
        mutate(spec)
        errors = check_spec(spec)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_every_sample_spec_is_valid(self):
        for path in sorted(SPECS.glob("*.json")):
            with self.subTest(path.name):
                self.assertEqual(check_spec(json.loads(path.read_text(encoding="utf-8"))), [])

    def test_required_fields(self):
        for key in ("issue", "title", "base", "compatibility", "layout", "layout_reason", "execution_root", "setup",
                    "root_cause", "target_behavior", "acceptance", "evidence", "decisions", "objectives", "gates",
                    "pr_rows", "follow_up", "rollback", "security"):
            with self.subTest(key):
                spec = sample("phased-related-flows")
                del spec[key]
                self.assertTrue(check_spec(spec), key)

    def test_value_shapes(self):
        self.assertSpecRejected(lambda s: s.update(issue="https://github.com/example/service/pull/3"), "issue:")
        self.assertSpecRejected(lambda s: s.update(base="dev"), "base:")
        self.assertSpecRejected(lambda s: s.update(execution_root="work/service"), "execution_root:")
        self.assertSpecRejected(lambda s: s.update(planned="soon"), "planned:")
        self.assertSpecRejected(lambda s: s.update(title="two\nlines"), "title:")
        self.assertSpecRejected(lambda s: s.update(compatibility="both"), "compatibility:")

    def test_compact_takes_exactly_one_objective(self):
        self.assertSpecRejected(lambda s: s.update(layout="compact"), "compact layout takes exactly one objective")

    def test_acceptance_rules(self):
        self.assertSpecRejected(lambda s: s["acceptance"][0].update(id="X1"), "unique AC<n> id")
        self.assertSpecRejected(lambda s: s["acceptance"][1].update(id="AC1"), "unique AC<n> id")
        self.assertSpecRejected(lambda s: s["acceptance"][0].update(objectives=[9]), "objective numbers within range")
        self.assertSpecRejected(lambda s: s["acceptance"].__setitem__(slice(None), [s["acceptance"][0]]), "objective 2 has no acceptance criterion")

    def test_sensitive_work_needs_controls_and_review(self):
        self.assertSpecRejected(lambda s: s["security"].pop("review"), "review", name="sensitive-phased")
        self.assertSpecRejected(lambda s: s["security"].update(controls=[]), "sensitive work needs S<n> controls", name="sensitive-phased")
        self.assertSpecRejected(lambda s: s["security"]["controls"][1].update(id="S1"), "unique S<n> id", name="sensitive-phased")
        self.assertSpecRejected(lambda s: s["security"]["controls"][0].update(objectives=[7]), "objective numbers within range", name="sensitive-phased")
        self.assertSpecRejected(lambda s: s["security"]["controls"][0].update(text="a\nb"), "single line", name="sensitive-phased")

    def test_pr_rows_cover_each_objective_once(self):
        self.assertSpecRejected(lambda s: s["pr_rows"][0].update(objectives=[1, 2]), "objective 3 must be in exactly one row")
        self.assertSpecRejected(lambda s: s["pr_rows"].append(dict(s["pr_rows"][0])), "objective 1 must be in exactly one row (found 2)")
        self.assertSpecRejected(lambda s: s["pr_rows"][0].update(keyword="Fixes"), "keyword")
        self.assertSpecRejected(lambda s: s["pr_rows"][0].update(branch="has space"), "branch")

    def test_objective_fields_and_wait(self):
        self.assertSpecRejected(lambda s: s["objectives"][0].pop("tests"), "tests:")
        self.assertSpecRejected(lambda s: s["objectives"][0].update(validate="a\nb"), "validate:")
        self.assertSpecRejected(lambda s: s["objectives"][0].update(prerequisites=[]), "prerequisites:")
        self.assertSpecRejected(lambda s: s["objectives"][0].update(wait={"on": "x"}), "wait:", name="phased-related-flows")
        self.assertSpecRejected(lambda s: s["objectives"][0].update(wait="later"), "wait:", name="phased-related-flows")

    def test_non_object_spec(self):
        self.assertEqual(check_spec([]), ["spec must be a JSON object"])


class RoutingAndTokenDiscipline(unittest.TestCase):
    def test_rules_block_is_byte_identical_in_every_file(self):
        for name in ("sensitive-phased", "multi-pr", "compact-bounded"):
            _, files = files_for(name)
            for filename, text in files.items():
                with self.subTest(f"{name}/{filename}"):
                    self.assertIn(RULES, text)

    def test_phase_rule_matches_file_kind(self):
        _, files = files_for("phased-indivisible")
        self.assertIn(PHASE_RULE["objective"], files["33-exec-obj-1.md"])
        self.assertIn(PHASE_RULE["gates"], files["33-exec-gates.md"])
        self.assertIn(PHASE_RULE["ship"], files["33-exec-ship.md"])
        _, compact = files_for("compact-bounded")
        self.assertIn(PHASE_RULE["compact"], compact["17-exec.md"])

    def test_objective_file_carries_only_its_own_facts(self):
        _, files = files_for("phased-related-flows")
        first, second = files["21-exec-obj-1.md"], files["21-exec-obj-2.md"]
        self.assertIn("src/recovery/recover.py:40", first)
        self.assertNotIn("src/rotation/rotate.py", first)
        self.assertNotIn("src/devices/manage.py", first)
        self.assertIn("- AC1:", first)
        self.assertNotIn("- AC2:", first)
        self.assertIn("src/rotation/rotate.py:55", second)
        self.assertNotIn("recover.py", second)
        self.assertIn("src/core/account_state.py:9", first + second)

    def test_adding_work_for_another_objective_never_grows_this_objective_file(self):
        spec = sample("phased-related-flows")
        issue = "21"
        before = render(spec, issue, "/work/plans")
        spec["evidence"].append({"at": "src/devices/extra.py:5", "claim": "x" * 400, "objectives": [3]})
        spec["decisions"].append({"text": "extra", "why": "y" * 400, "rejected": "z", "objectives": [3]})
        after = render(spec, issue, "/work/plans")
        for number in (1, 2):
            self.assertEqual(before[f"{issue}-exec-obj-{number}.md"], after[f"{issue}-exec-obj-{number}.md"])
        self.assertNotEqual(before[f"{issue}-exec-obj-3.md"], after[f"{issue}-exec-obj-3.md"])

    def test_freshness_lists_only_the_files_own_evidence_paths(self):
        _, files = files_for("phased-related-flows")
        line = next(l for l in files["21-exec-obj-2.md"].splitlines() if l.startswith("Freshness:"))
        self.assertIn("src/rotation/rotate.py", line)
        self.assertIn("src/core/account_state.py", line)
        self.assertNotIn("recover.py", line)
        self.assertIn("git diff --stat 0123abcdef origin/dev --", line)

    def test_security_controls_route_by_objective_and_are_complete_in_gates_and_ship(self):
        _, files = files_for("sensitive-phased")
        obj1, obj2 = files["41-exec-obj-1.md"], files["41-exec-obj-2.md"]
        self.assertIn("- S1:", obj1)
        self.assertNotIn("- S1:", obj2)
        self.assertIn("- S2:", obj2)
        self.assertIn("Security-sensitive: yes", obj2)
        for name in ("41-exec-gates.md", "41-exec-ship.md"):
            self.assertIn("- S1:", files[name])
            self.assertIn("- S2:", files[name])
            self.assertIn("Review:", files[name])

    def test_objective_without_controls_is_not_marked_sensitive(self):
        spec = sample("sensitive-phased")
        spec["security"]["controls"][0]["objectives"] = [1]
        spec["security"]["controls"][1]["objectives"] = [1]
        files = render(spec, "41", "/work/plans")
        self.assertIn("Security-sensitive: no", files["41-exec-obj-2.md"])
        self.assertIn("No issue-specific controls apply here", files["41-exec-obj-2.md"])

    def test_branch_creation_and_prerequisites(self):
        _, files = files_for("multi-pr")
        self.assertIn("create it from origin/dev", files["63-exec-obj-1.md"])
        self.assertIn("Prerequisites: none.", files["63-exec-obj-1.md"])
        self.assertIn("reuse the existing branch", files["63-exec-obj-2.md"])
        self.assertIn("objective(s) 1 committed and tested", files["63-exec-obj-2.md"])
        self.assertIn("create it from origin/fix/rounding-core", files["63-exec-obj-3.md"])
        self.assertIn("objective(s) 1,2 committed and tested", files["63-exec-obj-3.md"])

    def test_external_wait_opens_the_file(self):
        _, files = files_for("external-wait")
        text = files["52-exec.md"]
        self.assertLess(text.index("STOP: waits on: provider v2 deployed to dev"), text.index("## Rules"))
        self.assertIn("resume: exit 0", text)

    def test_ship_and_compact_files_carry_publication_controls(self):
        _, phased = files_for("multi-pr")
        _, compact = files_for("compact-bounded")
        for text in (phased["63-exec-ship.md"], compact["17-exec.md"]):
            self.assertIn("- PR1: branch=", text)
            self.assertIn("Rollback: Revert the PR", text)
            self.assertIn("Never merge", text)
            self.assertIn("issue body", text)
            self.assertIn("Report gaps first", text)
        self.assertIn("- PR2: branch=test/rounding-e2e; base=fix/rounding-core; objectives=3; keyword=Closes", phased["63-exec-ship.md"])

    def test_objective_files_never_publish(self):
        _, files = files_for("phased-related-flows")
        for number in (1, 2, 3):
            text = files[f"21-exec-obj-{number}.md"]
            self.assertNotIn("## Ship", text)
            self.assertNotIn("PR rows", text)
            self.assertIn("No push, PR or full gate suite", text)

    def test_every_file_posts_decisions_at_once_and_ship_adds_no_summary_comment(self):
        for name in ("compact-bounded", "phased-related-flows"):
            _, files = files_for(name)
            for filename, text in files.items():
                with self.subTest(f"{name}/{filename}"):
                    self.assertIn("post it at once as one issue comment, `Execution decision:", text)
                    self.assertIn("never repost", text)
        _, phased = files_for("phased-indivisible")
        ship = phased["33-exec-ship.md"]
        self.assertIn("decision comments (Rules) are standing", ship)
        self.assertNotIn("post one concise decision record", ship)
        self.assertNotIn("No push or PR, issue comment", phased["33-exec-gates.md"])

    def test_cleanup_lists_the_files_actually_written(self):
        _, files = files_for("phased-indivisible", "/tmp/plans dir")
        cleanup = files["33-exec-ship.md"].split("## Cleanup")[1]
        for name in files:
            self.assertIn(f"/tmp/plans dir/{name}", cleanup)
        self.assertIn("/tmp/plans dir/33-plan-progress.md", cleanup)

    def test_sample_files_stay_inside_their_token_budgets(self):
        kinds = {"exec.md": "compact", "gates.md": "gates", "ship.md": "ship"}
        for name in ("compact-bounded", "phased-related-flows", "sensitive-phased", "multi-pr"):
            _, files = files_for(name)
            for filename, text in files.items():
                kind = next((k for suffix, k in kinds.items() if filename.endswith(suffix)), "objective")
                with self.subTest(f"{name}/{filename}"):
                    self.assertLess(est_tokens(text), TOKEN_BUDGET[kind] // 2 + 400)

    def test_no_planner_facing_vocabulary_leaks_into_handoffs(self):
        for name in ("compact-bounded", "phased-related-flows"):
            _, files = files_for(name)
            for text in files.values():
                for word in ("teammate", "Claude", "Anthropic", "plan-flow", "canonical"):
                    self.assertNotIn(word, text)


class WriteSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def names(self):
        return sorted(p.name for p in self.out.iterdir())

    def test_valid_spec_writes_validated_files(self):
        spec = sample("phased-indivisible")
        result = run(spec, self.out)
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.names(), ["33-exec-gates.md", "33-exec-obj-1.md", "33-exec-ship.md"])
        self.assertEqual(sorted(Path(p).name for p in result["written"]), self.names())
        self.assertIn(str(self.out.resolve()), (self.out / "33-exec-ship.md").read_text(encoding="utf-8"))

    def test_invalid_spec_writes_nothing(self):
        spec = sample("phased-indivisible")
        del spec["rollback"]
        result = run(spec, self.out)
        self.assertFalse(result["ok"])
        self.assertEqual(self.names(), [])

    def test_validator_failure_on_rendered_text_writes_nothing(self):
        spec = sample("compact-bounded")
        spec["follow_up"] = "TBD"
        result = run(spec, self.out)
        self.assertFalse(result["ok"])
        self.assertTrue(any("placeholder" in e for e in result["errors"]), result)
        self.assertEqual(self.names(), [])

    def test_missing_planning_directory_is_reported_not_created(self):
        result = run(sample("compact-bounded"), self.out / "docs" / "plans")
        self.assertFalse(result["ok"])
        self.assertFalse((self.out / "docs").exists())

    def test_existing_files_need_explicit_replacement_and_stale_layouts_block(self):
        spec = sample("compact-bounded")
        self.assertTrue(run(spec, self.out)["ok"])
        first = (self.out / "17-exec.md").read_bytes()
        blocked = run(spec, self.out)
        self.assertFalse(blocked["ok"])
        self.assertIn("--replace-existing", blocked["errors"][0])
        self.assertEqual((self.out / "17-exec.md").read_bytes(), first)
        spec["title"] = "Changed title"
        self.assertTrue(run(spec, self.out, replace_existing=True)["ok"])
        self.assertIn("Changed title", (self.out / "17-exec.md").read_text(encoding="utf-8"))
        phased = sample("phased-indivisible")
        phased["issue"] = phased["issue"].replace("/33", "/17")
        stale = run(phased, self.out, replace_existing=True)
        self.assertFalse(stale["ok"])
        self.assertIn("would conflict: 17-exec.md", stale["errors"][0])
        self.assertTrue((self.out / "17-exec.md").exists())
        self.assertEqual(self.names(), ["17-exec.md"])

    def test_legacy_canonical_prompt_blocks_the_render_and_is_left_alone(self):
        legacy = self.out / "17-implementation-prompt.md"
        legacy.write_text("old canonical prompt", encoding="utf-8")
        result = run(sample("compact-bounded"), self.out, replace_existing=True)
        self.assertFalse(result["ok"])
        self.assertIn("would conflict: 17-implementation-prompt.md", result["errors"][0])
        self.assertEqual(legacy.read_text(encoding="utf-8"), "old canonical prompt")
        self.assertEqual(self.names(), ["17-implementation-prompt.md"])

    def test_other_issues_files_are_left_alone(self):
        (self.out / "99-exec.md").write_text("another issue", encoding="utf-8")
        self.assertTrue(run(sample("compact-bounded"), self.out)["ok"])
        self.assertEqual((self.out / "99-exec.md").read_text(encoding="utf-8"), "another issue")

    def test_command_line_reads_stdin_and_sets_exit_code(self):
        spec = sample("compact-bounded")
        done = subprocess.run([sys.executable, str(RENDERER), "--out", str(self.out)], input=json.dumps(spec),
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(json.loads(done.stdout)["ok"])
        again = subprocess.run([sys.executable, str(RENDERER), "--out", str(self.out)], input=json.dumps(spec),
                               capture_output=True, text=True, check=False)
        self.assertEqual(again.returncode, 1)
        broken = subprocess.run([sys.executable, str(RENDERER), "--out", str(self.out)], input="{not json",
                                capture_output=True, text=True, check=False)
        self.assertEqual(broken.returncode, 1)
        self.assertIn("cannot read spec", broken.stdout)


if __name__ == "__main__":
    unittest.main()
