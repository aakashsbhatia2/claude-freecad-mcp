"""Working with the document as a whole: undo, saving, the view, export."""

import os

import FreeCAD
import FreeCADGui

from ai_cad.util import body_of, document, find, rounded, solid_volume

VIEWS = {
    "isometric": "viewIsometric", "top": "viewTop", "bottom": "viewBottom",
    "front": "viewFront", "rear": "viewRear", "left": "viewLeft", "right": "viewRight",
}


def new_document(arguments):
    name = (arguments.get("name") or "Unnamed").strip()
    doc = FreeCAD.newDocument(name)
    FreeCAD.setActiveDocument(doc.Name)
    return "Created document '%s'. It is the active one now." % doc.Label


def _open_documents():
    return list(FreeCAD.listDocuments().values())


def _document_named(name):
    for doc in _open_documents():
        if name in (doc.Name, doc.Label):
            return doc
    return None


def _open_list():
    docs = _open_documents()
    if not docs:
        return "No documents are open."
    return "Open documents: %s." % ", ".join("'%s'" % d.Label for d in docs)


def switch_document(arguments):
    """Make another open document the one every tool works on."""
    name = arguments.get("name")
    doc = _document_named(name) if name else None
    if doc is None:
        return "There is no open document called '%s'. %s" % (name, _open_list())

    FreeCAD.setActiveDocument(doc.Name)
    try:
        FreeCADGui.setActiveDocument(doc.Name)
    except Exception:
        pass

    # The GUI can keep another tab in front, and the tools follow the GUI.
    # Say so rather than carry on in the wrong file.
    gui = FreeCADGui.ActiveDocument
    if gui is None or gui.Document.Name != doc.Name:
        return ("Could not bring '%s' to the front. Ask the user to click its "
                "tab in FreeCAD, then check with list_objects." % doc.Label)
    return "'%s' is the active document now." % doc.Label


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


def _exportable(arguments):
    """The object to write, from the document asked for.

    Asking for a document by name keeps an export from following whichever
    tab the user last clicked: two open parts both had a Pad001, and the bar
    was written into the splice's file.
    """
    wanted = arguments.get("document")
    if wanted:
        doc = _document_named(wanted)
        if doc is None:
            return None, "There is no open document called '%s'. %s" % (
                wanted, _open_list())
    else:
        doc = document()
    if doc is None:
        return None, "No document is open. Use new_document to start one."

    name = arguments.get("name")
    if name:
        obj = doc.getObject(name)
        if obj is None:
            matches = doc.getObjectsByLabel(name)
            obj = matches[0] if matches else None
        if obj is None:
            return None, "There is no object called '%s' in '%s'." % (name, doc.Label)
        body = body_of(obj)
        # A feature partway through the tree is a half-built part.
        if body is not None and body.Tip is not obj:
            return None, ("%s is partway through %s, so exporting it would "
                          "write a half-built part. Export %s instead." % (
                              obj.Label, body.Label, body.Label))
        return obj, None

    bodies = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]
    if len(bodies) == 1:
        return bodies[0], None
    if not bodies:
        return None, "There is no body in '%s' to export." % doc.Label
    return None, "'%s' has several bodies -- say which one: %s." % (
        doc.Label, ", ".join(b.Label for b in bodies))


def _what_was_written(obj, path):
    """Enough to tell two parts apart from the reply alone."""
    box = obj.Shape.BoundBox
    return "Exported %s from '%s' to %s (%s): %s x %s x %s mm, %s mm3." % (
        obj.Label, obj.Document.Label, path, _written(path),
        rounded(box.XLength), rounded(box.YLength), rounded(box.ZLength),
        rounded(solid_volume(obj)))


# Triangle formats FreeCAD writes from one call, picked by extension.
# 3MF is a container that records the unit; an STL is bare triangles with
# no units at all, which is why a slicer has to be told the scale.
MESH_FORMATS = ("stl", "3mf", "obj")


def _written(path):
    """File size in the unit that does not read as a failure.

    A small bracket is under a kilobyte, and "(0 KB)" looks like nothing
    came out.
    """
    size = os.path.getsize(path) if os.path.exists(path) else 0
    return "%d KB" % (size // 1024) if size >= 1024 else "%d bytes" % size


def export_mesh(arguments):
    """Triangles for a slicer, in whichever of the mesh formats was asked for."""
    import Mesh

    obj, error = _exportable(arguments)
    if error:
        return error

    path = os.path.expanduser(str(arguments["path"]))
    fmt = str(arguments.get("format") or "").lower().lstrip(".")
    if not fmt:
        # Nothing said: believe the extension already on the path, else STL.
        suffix = os.path.splitext(path)[1].lower().lstrip(".")
        fmt = suffix if suffix in MESH_FORMATS else "stl"
    if fmt not in MESH_FORMATS:
        return "Format must be one of: %s." % ", ".join(MESH_FORMATS)

    if not path.lower().endswith("." + fmt):
        path += "." + fmt

    Mesh.export([obj], path)
    return _what_was_written(obj, path)


def export_step(arguments):
    """STEP keeps the real curved surfaces, for handing to other CAD."""
    import Part

    obj, error = _exportable(arguments)
    if error:
        return error

    path = os.path.expanduser(str(arguments["path"]))
    if not path.lower().endswith((".step", ".stp")):
        path += ".step"

    Part.export([obj], path)
    return _what_was_written(obj, path)


HANDLERS = {
    "new_document": new_document,
    "switch_document": switch_document,
    "undo": undo,
    "save_document": save_document,
    "fit_view": fit_view,
    "set_view": set_view,
    "measure": measure,
    "export_mesh": export_mesh,
    "export_step": export_step,
}
