"""Preflight checks against throwaway repositories; nothing outside the temp directory is touched."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PREFLIGHT = Path(__file__).with_name("preflight.py")
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "protocol.file.allow=always"]


def git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True)


def init_repo(path, *, branch="dev"):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", branch)
    (path / "README.md").write_text("x", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")


def preflight(cwd):
    done = subprocess.run([sys.executable, str(PREFLIGHT)], cwd=cwd, capture_output=True, text=True, check=False,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"})
    assert done.returncode == 0, done.stderr
    return done.stdout


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_outside_a_repository_asks_for_the_anchor(self):
        out = preflight(self.root)
        self.assertIn("repo: none", out)
        self.assertNotIn("branch:", out)

    def test_standalone_repository_facts(self):
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "AGENTS.md").write_text("rules", encoding="utf-8")
        (repo / "scratch.txt").write_text("x", encoding="utf-8")
        out = preflight(repo)
        self.assertIn("role: standalone repository", out)
        self.assertIn("branch: dev", out)
        self.assertIn("dirty: 2 path(s)", out)
        self.assertIn("?? scratch.txt", out)
        self.assertIn(str(repo / "AGENTS.md"), out)
        self.assertIn("profile: none", out)
        self.assertIn("docs/plans: missing", out)

    def test_planning_directory_ignore_state(self):
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "docs" / "plans").mkdir(parents=True)
        self.assertIn("NOT ignored", preflight(repo))
        (repo / ".gitignore").write_text("docs/plans/\n", encoding="utf-8")
        self.assertIn("exists, ignored by git", preflight(repo))

    def test_dirty_listing_is_capped(self):
        repo = self.root / "repo"
        init_repo(repo)
        for index in range(40):
            (repo / f"file{index}.txt").write_text("x", encoding="utf-8")
        out = preflight(repo)
        self.assertIn("dirty: 40 path(s)", out)
        self.assertIn("... 25 more dirty paths", out)
        self.assertLess(len(out.splitlines()), 30)

    def test_submodule_and_parent_roles_and_agents_chain(self):
        child = self.root / "child"
        init_repo(child)
        (child / "AGENTS.md").write_text("child rules", encoding="utf-8")
        git(child, "add", "-A")
        git(child, "commit", "-q", "-m", "agents")
        parent = self.root / "parent"
        init_repo(parent, branch="main")
        (parent / "AGENTS.md").write_text("parent rules", encoding="utf-8")
        git(parent, "submodule", "add", "-q", str(child), "sdk/child")
        git(parent, "add", "-A")
        git(parent, "commit", "-q", "-m", "mount")

        from_parent = preflight(parent)
        self.assertIn("role: parent checkout with submodules", from_parent)
        self.assertIn("submodules: 0 of 1 uninitialized", from_parent)

        sub = parent / "sdk" / "child"
        from_child = preflight(sub)
        self.assertIn(f"role: submodule (superproject {parent})", from_child)
        chain = next(line for line in from_child.splitlines() if line.startswith("guidance chain:"))
        self.assertLess(chain.index(str(sub / "AGENTS.md")), chain.index(str(parent / "AGENTS.md")))

        nested = sub / "inner"
        nested.mkdir()
        self.assertIn(str(parent / "AGENTS.md"), preflight(nested))

        git(parent, "submodule", "deinit", "-q", "-f", "sdk/child")
        self.assertIn("submodules: 1 of 1 uninitialized", preflight(parent))
        self.assertIn("  sdk/child", preflight(parent))

    def test_preflight_modifies_nothing(self):
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "a.txt").write_text("x", encoding="utf-8")
        before = sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)
        status = subprocess.run([*GIT, "status", "--short"], cwd=repo, capture_output=True, text=True, check=True).stdout
        preflight(repo)
        after = sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after)
        self.assertEqual(status, subprocess.run([*GIT, "status", "--short"], cwd=repo, capture_output=True, text=True, check=True).stdout)

    def test_claude_md_joins_the_guidance_chain_and_profile_is_reported(self):
        repo = self.root / "repo"
        init_repo(repo)
        (repo / "CLAUDE.md").write_text("rules", encoding="utf-8")
        (repo / ".claude").mkdir()
        (repo / ".claude" / "dev-flow-context.md").write_text("profile", encoding="utf-8")
        out = preflight(repo)
        self.assertIn(str(repo / "CLAUDE.md"), out)
        self.assertIn("profile: .claude/dev-flow-context.md", out)

    def test_remote_default_branch_comes_first(self):
        origin = self.root / "origin"
        init_repo(origin, branch="trunk")
        clone = self.root / "clone"
        subprocess.run([*GIT, "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
        self.assertIn("remote base branches: trunk (first is the remote default)", preflight(clone))

    def test_arguments_are_ignored(self):
        repo = self.root / "repo"
        init_repo(repo)
        done = subprocess.run([sys.executable, str(PREFLIGHT), "; touch pwned"], cwd=repo, capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0)
        self.assertFalse((repo / "pwned").exists())


if __name__ == "__main__":
    unittest.main()
