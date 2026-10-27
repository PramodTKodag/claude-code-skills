"""Skill instructions must run unchanged on Claude Code, Codex and Cursor, so no host-only construct may appear in them."""

from pathlib import Path
import re
import unittest

SKILL_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTION_FILES = [SKILL_ROOT / "SKILL.md", *sorted((SKILL_ROOT / "references").glob("*.md"))]

HOST_ONLY = {
    "Claude skill-directory variable": re.compile(r"CLAUDE_SKILL_DIR"),
    "Claude question tool": re.compile(r"AskUserQuestion"),
    "shell-injection line": re.compile(r"^!`", re.MULTILINE),
}


class PortabilityTests(unittest.TestCase):
    def test_instructions_use_no_host_only_constructs(self):
        for path in INSTRUCTION_FILES:
            text = path.read_text(encoding="utf-8")
            for label, pattern in HOST_ONLY.items():
                with self.subTest(file=path.name, construct=label):
                    self.assertIsNone(pattern.search(text), f"{path.name} uses a {label}")

    def test_script_paths_use_the_skill_dir_placeholder(self):
        text = "\n".join(path.read_text(encoding="utf-8") for path in INSTRUCTION_FILES)
        for script in ("preflight.py", "render_handoff.py", "decisions_lookup.py"):
            with self.subTest(script=script):
                self.assertIn(f"<skill-dir>/scripts/{script}", text)


if __name__ == "__main__":
    unittest.main()
