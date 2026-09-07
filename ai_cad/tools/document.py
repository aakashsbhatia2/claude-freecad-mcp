"""Working with the document as a whole: undo, saving, the view, export."""

import os

import FreeCAD
import FreeCADGui

from ai_cad.util import document, find, rounded

VIEWS = {
    "isometric": "viewIsometric", "top": "viewTop", "bottom": "viewBottom",
    "front": "viewFront", "rear": "viewRear", "left": "viewLeft", "right": "viewRight",
}


def new_document(arguments):
    name = (arguments.get("name") or "Unnamed").strip()
    doc = FreeCAD.newDocument(name)
    FreeCAD.setActiveDocument(doc.Name)
    return "Created document '%s'. It is the active one now." % doc.Label


def undo(_arguments):
    doc = document()
    if doc is None:
        return "No document is open. Use new_document to start one."
    if not doc.UndoNames:
        return "There is nothing to undo."
    name = doc.UndoNames[0]
    doc.undo()
    doc.recompute()
    return "Undid '%s'." % name


def save_document(arguments):
    doc = document()
    if doc is None:
        return "No document is open. Use new_document to start one."

    path = arguments.get("path")
    if path:
        path = os.path.expanduser(path)
        if not path.lower().endswith(".fcstd"):
            path += ".FCStd"
        doc.saveAs(path)
        return "Saved to %s." % path

    if not doc.FileName:
        return "This document has never been saved -- give me a path to save it to."
    doc.save()
    return "Saved %s." % doc.FileName


def fit_view(_arguments):
    FreeCADGui.SendMsgToActiveView("ViewFit")
    return "Zoomed to fit."


def set_view(arguments):
    name = str(arguments.get("direction", "isometric")).lower()
    if name not in VIEWS:
        return "View must be one of: %s." % ", ".join(sorted(VIEWS))
    view = FreeCADGui.ActiveDocument.ActiveView
    getattr(view, VIEWS[name])()
    FreeCADGui.SendMsgToActiveView("ViewFit")
    return "Looking from the %s." % name


def measure(_arguments):
    """Shortest distance between the two things the user has clicked."""
    selection = FreeCADGui.Selection.getSelectionEx()
    shapes = [sub for entry in selection for sub in entry.SubObjects]
    if len(shapes) < 2:
        for entry in selection:
            if not entry.SubElementNames and getattr(entry.Object, "Shape", None):
                shapes.append(entry.Object.Shape)
    if len(shapes) < 2:
        return "Select two things to measure between."

    distance, points, _ = shapes[0].distToShape(shapes[1])
    start, end = points[0]
    return "Shortest distance is %s mm, from (%s, %s, %s) to (%s, %s, %s)." % (
        rounded(distance),
        rounded(start.x), rounded(start.y), rounded(start.z),
        rounded(end.x), rounded(end.y), rounded(end.z))


def _exportable(name):
    if name:
        obj = find(name)
        if obj is None:
            return None, "There is no object called '%s'." % name
        return obj, None

    doc = document()
    if doc is None:
        return None, "No document is open. Use new_document to start one."
    bodies = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]
    if len(bodies) == 1:
        return bodies[0], None
    if not bodies:
        return None, "There is no body to export."
    return None, "There are several bodies -- say which one: %s." % ", ".join(
        b.Label for b in bodies)


def export_stl(arguments):
    """STL for slicing. Deviation controls how finely curves are triangulated."""
    import Mesh

    obj, error = _exportable(arguments.get("name"))
    if error:
        return error

    path = os.path.expanduser(str(arguments["path"]))
    if not path.lower().endswith(".stl"):
        path += ".stl"

    Mesh.export([obj], path)
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return "Exported %s to %s (%d KB)." % (obj.Label, path, size // 1024)


def export_step(arguments):
    """STEP keeps the real curved surfaces, for handing to other CAD."""
    import Part

    obj, error = _exportable(arguments.get("name"))
    if error:
        return error

    path = os.path.expanduser(str(arguments["path"]))
    if not path.lower().endswith((".step", ".stp")):
        path += ".step"

    Part.export([obj], path)
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return "Exported %s to %s (%d KB)." % (obj.Label, path, size // 1024)


HANDLERS = {
    "new_document": new_document,
    "undo": undo,
    "save_document": save_document,
    "fit_view": fit_view,
    "set_view": set_view,
    "measure": measure,
    "export_stl": export_stl,
    "export_step": export_step,
}
