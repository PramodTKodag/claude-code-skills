"""Constants and parsers shared by the render and validate scripts."""

import re

SECTIONS = {
    "compact": ("Workspace", "Acceptance", "Evidence", "Decisions", "Objective", "Security", "Gates", "Ship", "Follow-up", "Cleanup", "Stops"),
    "objective": ("Workspace", "Acceptance", "Evidence", "Decisions", "Objective", "Security", "Validate", "Record", "Stops"),
    "gates": ("Workspace", "Scope", "Acceptance map", "Security", "Gates", "Record", "Stops"),
    "ship": ("Workspace", "Acceptance map", "Evidence", "Decisions", "Security", "Gates", "Ship", "Follow-up", "Cleanup", "Stops"),
}

# Soft per-file budgets in estimated tokens (chars / 4), about twice what the sample specs in
# evals/specs render to. A file over budget is a signal to trim prose or re-check sizing,
# never a reason to drop a fact, control, test or stop.
TOKEN_BUDGET = {"compact": 3200, "objective": 2200, "gates": 1800, "ship": 2600}

EXEC_MARKER = "This is an execution prompt."
EXEC_SENTENCE = (
    f"{EXEC_MARKER} When the user pastes it as their instruction in a new coding session, "
    "execute its scoped work after the freshness and safety checks; no extra start command or design "
    "approval is needed. Reading it as reference or generating it during planning does not authorize execution."
)

PR_ROW_FORMAT = "- PR{n}: branch={branch}; base={base}; objectives={objectives}; keyword={keyword}"
PR_ROW = re.compile(
    r"^- PR(\d+): branch=([^;\s]+); base=([^;\s]+); objectives=(\d+(?:,\d+)*); keyword=(Closes|Refs)\s*$",
    re.MULTILINE,
)
BASE_VALUE = re.compile(r"([^\s@]+)@([0-9a-f]{7,40})")
DATE_VALUE = re.compile(r"\d{4}-\d{2}-\d{2}")
ISSUE_URL = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/issues/([1-9][0-9]*)")
AC_ID = re.compile(r"\bAC[1-9][0-9]*\b")
CONTROL_LINE = re.compile(r"^- (S[1-9][0-9]*):\s*(.+)$", re.MULTILINE)
ABSOLUTE_PATH = re.compile(r"(?:^|[\s`(:=])/[\w.\-]+(?:/[\w.\-]+)*")


def header(text):
    """Metadata block: everything before the first level-two heading."""
    return text.split("\n## ", 1)[0]


def field(text, name):
    """Value of a `Name: value` metadata line, read from the header only."""
    match = re.search(r"^" + re.escape(name) + r":[ \t]*(.+)$", header(text), re.MULTILINE)
    return match.group(1).strip() if match else ""


def sections(text):
    matches = list(re.finditer(r"^## (.+)$", text, re.MULTILINE))
    return {
        match.group(1).strip(): text[match.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        for i, match in enumerate(matches)
    }


def est_tokens(text):
    """Character-count proxy (chars / 4); not a measured token count."""
    return (len(text) + 3) // 4


def artifact_pattern(issue):
    """Matches any handoff artifact of this issue, including a stale canonical reference."""
    return re.compile(re.escape(issue) + r"-(?:exec(?:-obj-[1-9][0-9]*|-gates|-ship)?|implementation-prompt)\.md")


def phase_pattern(issue):
    return re.compile(re.escape(issue) + r"-exec-(?:obj-[1-9][0-9]*|gates|ship)\.md")
