"""claude-freecad-mcp -- FreeCAD driven over MCP.

Nothing here may import FreeCAD or Qt: the MCP server runs outside FreeCAD
and reads socket_path() from this module.
"""

import os
import tempfile


def socket_path():
    """Where FreeCAD listens. Both halves work it out the same way.

    In the system's temporary folder, named after the user so two people on
    one machine do not collide.
    """
    override = os.environ.get("CLAUDE_FREECAD_SOCKET")
    if override:
        return override
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "default"
    return os.path.join(tempfile.gettempdir(), "claude-freecad-%s.sock" % user)
