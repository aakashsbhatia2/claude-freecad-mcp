"""A log of every tool call, for watching what the model does.

Off unless CLAUDE_FREECAD_DEBUG=1. The MCP server appends one JSON line per
call; debug_panel.py shows the file as a page on localhost.

Nothing here may import FreeCAD or Qt: the MCP server writes this log with
FreeCAD closed.
"""

import json
import os
import tempfile


def enabled():
    return os.environ.get("CLAUDE_FREECAD_DEBUG", "").lower() in ("1", "true", "yes")


def log_path():
    """In the temporary folder, named after the user, like the socket."""
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "default"
    return os.path.join(tempfile.gettempdir(), "claude-freecad-debug-%s.jsonl" % user)


def record(entry):
    """Append one entry. Never raises: a log must not break a tool call."""
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def read(limit=500):
    """The last <limit> entries, oldest first. Unreadable lines are skipped."""
    try:
        with open(log_path(), encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def clear():
    try:
        os.remove(log_path())
    except OSError:
        pass
