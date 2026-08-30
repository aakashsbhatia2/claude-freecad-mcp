"""Loaded by FreeCAD at startup.

Everything real lives in the ai_cad package: FreeCAD executes this file with
separate globals and locals, which breaks name lookups inside any function or
class defined here.
"""

import FreeCADGui as Gui

import ai_cad.panel

ai_cad.panel.install(Gui.getMainWindow())
