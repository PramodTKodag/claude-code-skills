"""Renderer checks: spec validation, routing of facts per file, token discipline, write safety."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from handoff_common import TOKEN_BUDGET, est_tokens
from render_handoff import PHASE_RULE, PROGRESS_FORMAT, RULES, check_spec, render, run, spec_warnings

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

    def test_stacked_rows_form_one_chain_from_the_trunk(self):
        self.assertSpecRejected(lambda s: s["pr_rows"][1].update(base="not-a-row"),
                                "base must be dev or the branch of an earlier row", "multi-pr")

        def branch_the_stack(spec):
            spec["pr_rows"][0]["objectives"] = [1]
            spec["pr_rows"].insert(1, {"branch": "fix/other", "base": spec["pr_rows"][0]["branch"], "objectives": [2], "keyword": "Refs"})
        self.assertSpecRejected(branch_the_stack, "a stack is one chain", "multi-pr")

        self.assertSpecRejected(lambda s: s["pr_rows"].append(dict(s["pr_rows"][1], objectives=[9])), "repeats branch", "multi-pr")

    def test_stacked_objectives_build_upward_and_close_on_the_top(self):
        def lower_work_after_upper(spec):
            spec["pr_rows"][0]["objectives"] = [2, 3]
            spec["pr_rows"][1]["objectives"] = [1]
            spec["objectives"][2].pop("prerequisites")
        self.assertSpecRejected(lower_work_after_upper, "must all come after the objectives of the PR(s) it stacks on", "multi-pr")

        def close_on_the_bottom(spec):
            spec["pr_rows"][0]["keyword"], spec["pr_rows"][1]["keyword"] = "Closes", "Refs"
        self.assertSpecRejected(close_on_the_bottom, "Closes belongs on the top of the stack", "multi-pr")

        self.assertSpecRejected(lambda s: s["objectives"][0].update(prerequisites=[3]),
                                "objective 3 is not in this PR or a PR it stacks on", "multi-pr")

    def test_many_criteria_for_little_work_is_a_warning_not_an_error(self):
        spec = sample("compact-bounded")
        self.assertEqual(spec_warnings(spec), [])
        spec["acceptance"] += [{"id": f"AC{n}", "text": "extra", "objectives": [1]} for n in range(10, 15)]
        self.assertEqual(check_spec(spec), [])
        self.assertTrue(any("criteria for 1 objective(s)" in w for w in spec_warnings(spec)))

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
        stacked = files["63-exec-obj-3.md"]
        self.assertIn("create it from the local tip of fix/rounding-core", stacked)
        self.assertIn("`git switch -c test/rounding-e2e fix/rounding-core`", stacked)
        self.assertIn("unpushed by design: never wait for its PR, push or merge", stacked)
        self.assertNotIn("origin/fix/rounding-core", stacked)
        self.assertIn("objective(s) 1,2 committed and tested", stacked)

    def test_stacked_row_inherits_the_objectives_of_the_row_below_as_prerequisites(self):
        spec = sample("multi-pr")
        del spec["objectives"][2]["prerequisites"]
        files = render(spec, "63", "/work/plans")
        self.assertIn("objective(s) 1,2 committed and tested", files["63-exec-obj-3.md"])

    def test_only_a_stacked_ship_file_carries_the_stack_steps(self):
        _, stacked = files_for("multi-pr")
        _, single = files_for("phased-related-flows")
        self.assertIn("Stack: rows are one chain, bottom first", stacked["63-exec-ship.md"])
        self.assertIn("git rebase --onto origin/dev", stacked["63-exec-ship.md"])
        self.assertIn("`gh stack init -b dev <row branches in order>`, then `gh stack submit --auto`", stacked["63-exec-ship.md"])
        self.assertIn("marks them ready before `gh stack merge`", stacked["63-exec-ship.md"])
        self.assertIn("`gh pr create --draft --base <row base>`", stacked["63-exec-ship.md"])
        self.assertNotIn("Stack:", single["21-exec-ship.md"])

    def test_every_file_forbids_test_tampering_and_fake_passes(self):
        for name in ("compact-bounded", "multi-pr"):
            _, files = files_for(name)
            for filename, text in files.items():
                with self.subTest(f"{name}/{filename}"):
                    self.assertIn("Never delete, skip or weaken a test or assertion to get green", text)
                    self.assertIn("`no tests to run`, a zero count or an unmatched filter is a failure", text)

    def test_progress_file_is_json_with_one_criteria_entry_shape(self):
        text = PROGRESS_FORMAT.format(planning="/work/plans", issue="63")
        self.assertIn("/work/plans/63-plan-progress.json", text)
        shape = json.loads(text[text.index("{"):text.rindex("}") + 1])
        self.assertEqual(sorted(shape), ["comments", "criteria", "decisions", "done", "findings", "gates", "next", "prs"])
        self.assertEqual(shape["criteria"]["<AC id>"], {"status": "pending", "evidence": ""})
        self.assertIn("Edit values only, never remove or rename keys", text)

    def test_gates_and_ship_demand_evidence_per_criterion(self):
        _, files = files_for("multi-pr")
        self.assertIn("set every criteria entry to passing or failing with its evidence", files["63-exec-gates.md"])
        self.assertIn("Every criteria entry in the progress file must be `passing` with evidence", files["63-exec-ship.md"])
        self.assertIn("Report gaps first (criteria not passing", files["63-exec-ship.md"])

    def test_scope_check_lists_one_command_per_pr_in_gates_and_compact_files(self):
        _, phased = files_for("multi-pr")
        _, compact = files_for("compact-bounded")
        gates = phased["63-exec-gates.md"]
        self.assertIn("- PR1 scope: `git diff --name-only origin/dev...fix/rounding-core -- . ':!src/pricing/round.py' ':!src/display/format.py'`", gates)
        self.assertIn("- PR2 scope: `git diff --name-only fix/rounding-core...test/rounding-e2e -- . ':!tests/e2e/test_totals.py'`", gates)
        self.assertIn("- PR1 scope: `git diff --name-only origin/dev...fix/parse-id", compact["17-exec.md"])
        for text in (phased["63-exec-obj-1.md"], phased["63-exec-ship.md"]):
            self.assertNotIn("scope: `git diff", text)

    def test_scope_check_command_prints_only_paths_the_plan_did_not_name(self):
        _, files = files_for("compact-bounded")
        line = next(l for l in files["17-exec.md"].splitlines() if l.startswith("- PR1 scope:"))
        command = line.split("`")[1]
        with tempfile.TemporaryDirectory() as repo:
            def git(*args):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo, check=True, capture_output=True)
            git("init", "-q", "-b", "dev")
            Path(repo, "README.md").write_text("base\n")
            git("add", "README.md")
            git("commit", "-q", "-m", "base")
            git("update-ref", "refs/remotes/origin/dev", "HEAD")
            git("switch", "-q", "-c", "fix/parse-id")
            for path in ("src/parse.py", "tests/test_parse.py", "Package.resolved"):
                Path(repo, path).parent.mkdir(parents=True, exist_ok=True)
                Path(repo, path).write_text("x\n")
            git("add", "-A")
            git("commit", "-q", "-m", "work")
            out = subprocess.run(command, shell=True, cwd=repo, capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.split(), ["Package.resolved"])

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
        self.assertIn("decision and completion comments (Rules) are standing", ship)
        self.assertNotIn("post one concise decision record", ship)
        self.assertNotIn("No push or PR, issue comment", phased["33-exec-gates.md"])

    def test_every_phase_posts_one_completion_comment_only_when_its_work_is_done(self):
        _, phased = files_for("phased-indivisible")
        for name, text in phased.items():
            with self.subTest(name):
                self.assertIn("- Completion comment: once this phase's work is fully done (never partial", text)
                self.assertIn("A stop or failure posts nothing", text)
        self.assertIn("Completion comment (Rules) after the commit and passing validation", phased["33-exec-obj-1.md"])
        self.assertIn("Completion comment (Rules) after every criteria entry is set", phased["33-exec-gates.md"])
        self.assertIn("Completion comment (Rules), once every PR row is open", phased["33-exec-ship.md"])
        _, compact = files_for("compact-bounded")
        text = next(iter(compact.values()))
        self.assertIn("Completion comment (Rules) after the commit and passing validation", text)
        self.assertIn("Completion comment (Rules) after every criteria entry is set", text)
        self.assertIn("Completion comment (Rules), once every PR row is open", text)

    def test_cleanup_lists_the_files_actually_written(self):
        _, files = files_for("phased-indivisible", "/tmp/plans dir")
        cleanup = files["33-exec-ship.md"].split("## Cleanup")[1]
        for name in files:
            self.assertIn(f"/tmp/plans dir/{name}", cleanup)
        self.assertIn("/tmp/plans dir/33-plan-progress.json", cleanup)

    def test_progress_file_lives_in_the_planning_directory(self):
        _, files = files_for("phased-indivisible", "/tmp/plans dir")
        for name, text in files.items():
            self.assertNotIn("/work/service/33-plan-progress.json", text, name)
        self.assertIn("Progress file `/tmp/plans dir/33-plan-progress.json`", files["33-exec-obj-1.md"])

    def test_every_phase_asks_through_the_interactive_question_rule(self):
        _, files = files_for("phased-indivisible")
        for name, text in files.items():
            self.assertIn("- Questions: ask only via the host's interactive question tool", text, name)
            self.assertIn("recommended first", text, name)
            self.assertIn("ask the way forward (Questions)", text, name)
            self.assertIn("never wait silently", text, name)
        self.assertIn("ask `Push and open PRs (Recommended)` / `Hold`", files["33-exec-ship.md"])

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
