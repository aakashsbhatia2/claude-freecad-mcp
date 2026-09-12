#!/usr/bin/env python3
"""Refuse the tools Claude Code would otherwise use to work around a gap.

The FreeCAD tools are the whole product: a fixed set, each one a single undo
step. The moment the model is allowed to write a macro instead, the output
stops being predictable -- so the escape routes are closed rather than
discouraged.

Claude Code runs this before Bash, Write, Edit, NotebookEdit and Task (see
hooks/hooks.json). It denies every one of them. The reason string is written
for the model, not the user: it says what to do instead, because a refusal
with no alternative is just something to route around.

Set CLAUDE_FREECAD_STRICT=0 to turn this off -- needed to work on this repo,
since an enabled plugin applies in every project.
"""

import json
import os
import sys

REASON = (
    "The FreeCAD MCP tools are the only way to act here. Shell commands, "
    "file edits, FreeCAD macros and Python scripts are not available and "
    "will not become available. "
    "If none of the FreeCAD tools does what the user asked, tell the user "
    "plainly that it is not supported and stop -- do not write a macro or a "
    "script for them to run, and do not offer one."
)

OFF = ("0", "off", "false", "no")


def main():
    # Drained so Claude Code never blocks writing the payload. Nothing in it
    # is needed: the matcher in hooks.json already decided.
    sys.stdin.read()

    if os.environ.get("CLAUDE_FREECAD_STRICT", "").strip().lower() in OFF:
        return

    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": REASON,
    }}, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
