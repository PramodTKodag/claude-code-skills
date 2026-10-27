"""Read-only repository facts for planning, printed as short `key: value` lines.

Takes no arguments, so skill loading never passes user text to a shell. It runs `git` with
--no-optional-locks and reads nothing from the network except the optional `gh auth status` probe.
"""

import subprocess
import sys
from pathlib import Path

MAX_LISTED = 15
BASE_CANDIDATES = ("dev", "main", "master", "trunk")
GUIDANCE_FILES = ("AGENTS.md", "CLAUDE.md")
PROFILE_PATHS = (".agents/dev-flow-context.md", ".claude/dev-flow-context.md")


def run(args, cwd, timeout=8):
    """Stdout of a command, or None when it fails or is unavailable."""
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def git(cwd, *args):
    return run(["git", "--no-optional-locks", *args], cwd)


def capped(lines, label):
    shown = lines[:MAX_LISTED]
    extra = len(lines) - len(shown)
    return shown + ([f"... {extra} more {label}"] if extra > 0 else [])


def role(top, superproject):
    if superproject:
        return f"submodule (superproject {superproject})"
    if (Path(top) / ".gitmodules").is_file():
        return "parent checkout with submodules"
    return "standalone repository"


def guidance_chain(cwd, boundary):
    """AGENTS.md and CLAUDE.md files from cwd up to the outermost checkout, nearest first."""
    found, current = [], Path(cwd).resolve()
    limit = Path(boundary).resolve()
    while True:
        found.extend(str(current / name) for name in GUIDANCE_FILES if (current / name).is_file())
        if current == limit or current == current.parent:
            return found
        current = current.parent


def remote_bases(cwd):
    """Default branch from origin/HEAD first, then the common base names that exist on origin."""
    default = git(cwd, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    names = [default.removeprefix("origin/")] if default else []
    names += [b for b in BASE_CANDIDATES if b not in names and git(cwd, "rev-parse", "--verify", "-q", f"origin/{b}")]
    return names


def profile_files(top):
    return [path for path in PROFILE_PATHS if (Path(top) / path).is_file()]


def submodule_state(top):
    status = git(top, "submodule", "status")
    if not status:
        return []
    return [f"{'uninitialized' if line.startswith('-') else 'initialized'}: {line[1:].split()[1]}"
            for line in status.splitlines() if len(line[1:].split()) >= 2]


def planning_dir_state(top):
    planning = Path(top) / "docs" / "plans"
    if not planning.is_dir():
        return "docs/plans: missing (ask where handoffs belong)"
    probe = subprocess.run(["git", "check-ignore", "-q", "docs/plans/probe.md"], cwd=top, capture_output=True, check=False)
    ignored = probe.returncode == 0
    return "docs/plans: exists, ignored by git" if ignored else "docs/plans: exists, NOT ignored (new handoff files will show as untracked; ask the user)"


def main():
    cwd = Path.cwd()
    top = git(cwd, "rev-parse", "--show-toplevel")
    print(f"cwd: {cwd}")
    if not top:
        print("repo: none (cwd is not inside a git repository; ask for the anchor repo)")
        return 0
    superproject = git(cwd, "rev-parse", "--show-superproject-working-tree")
    print(f"repo: {top}")
    print(f"role: {role(top, superproject)}")
    print(f"branch: {git(cwd, 'branch', '--show-current') or '(detached)'}  head: {git(cwd, 'rev-parse', '--short', 'HEAD') or '(none)'}")
    print(f"upstream: {git(cwd, 'rev-parse', '--abbrev-ref', '@{u}') or '(none)'}")
    print(f"remote base branches: {', '.join(remote_bases(cwd)) or '(none found; resolve from the repo guidance)'} (first is the remote default)")
    dirty = (git(cwd, "status", "--short") or "").splitlines()
    print("dirty: " + ("none" if not dirty else f"{len(dirty)} path(s)"))
    for line in capped(dirty, "dirty paths"):
        print(f"  {line}")
    states = submodule_state(top)
    if states:
        missing = [s.split(": ", 1)[1] for s in states if s.startswith("uninitialized")]
        print(f"submodules: {len(missing)} of {len(states)} uninitialized")
        for line in capped(missing, "uninitialized submodules"):
            print(f"  {line}")
    boundary = superproject or top
    print("guidance chain: " + (", ".join(guidance_chain(cwd, boundary)) or "none found"))
    print("profile: " + (", ".join(profile_files(top)) or "none (no dev-flow context file)"))
    print(planning_dir_state(top))
    try:
        gh = subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=8, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        gh = False
    print(f"gh: {'authenticated' if gh else 'not authenticated or unavailable'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
