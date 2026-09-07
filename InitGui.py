"""Loaded by FreeCAD at startup.

Everything real lives in the ai_cad package: FreeCAD executes this file with
separate globals and locals, which breaks name lookups inside any function or
class defined here.
"""

import FreeCAD
import FreeCADGui as Gui

import ai_cad.server
import ai_cad.status

try:
    bridge = ai_cad.server.start(Gui.getMainWindow())
    ai_cad.status.install(Gui.getMainWindow(), bridge)
except Exception as exc:
    # A bridge that won't open must not stop FreeCAD from starting.
    FreeCAD.Console.PrintError("claude-freecad-mcp bridge: %s\n" % exc)
