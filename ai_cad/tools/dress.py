"""Fillets, chamfers and holes -- the operations applied to a finished solid.

These act on what the user has clicked. Working out which edge is "the top
left one" from a description alone is a separate, much harder problem.
"""

import FreeCADGui

from ai_cad.util import document, find, rounded

# Clearance drill sizes, so "an M4 clearance hole" means something.
CLEARANCE = {"M2": 2.4, "M2.5": 2.9, "M3": 3.4, "M4": 4.5, "M5": 5.5, "M6": 6.6, "M8": 9.0}


def _body(obj):
    """The body a feature belongs to, since dress-up features live in one."""
    if obj.TypeId == "PartDesign::Body":
        return obj
    for candidate in document().Objects:
        if candidate.TypeId == "PartDesign::Body" and obj in candidate.Group:
            return candidate
    return None


def _selected_edges():
    """Edges the user has clicked, grouped by the feature that owns them."""
    for entry in FreeCADGui.Selection.getSelectionEx():
        names = [n for n in entry.SubElementNames if n.startswith("Edge")]
        if names:
            return entry.Object, names
    return None, []


def _base_feature(obj):
    """A dress-up feature attaches to the solid, not to the body wrapper."""
    if obj.TypeId == "PartDesign::Body":
        return obj.Tip
    return obj


def _apply_dressup(kind, size_property, size, label):
    owner, edges = _selected_edges()
    if owner is None:
        return "No edges are selected. Ask the user to click the edges first."

    body = _body(owner)
    if body is None:
        return "%s is not inside a Part Design body." % owner.Label

    base = _base_feature(owner)
    feature = body.newObject("PartDesign::" + kind, kind)
    feature.Base = (base, edges)
    setattr(feature, size_property, float(size))

    doc = document()
    doc.recompute()
    if "Invalid" in getattr(feature, "State", []):
        error = getattr(feature, "Error", "no reason given")
        doc.removeObject(feature.Name)
        doc.recompute()
        return "That %s failed and was undone: %s" % (label, error)

    return "%s %d edge(s) at %s mm as %s." % (
        label, len(edges), rounded(size), feature.Name)


def fillet_edges(arguments):
    return _apply_dressup("Fillet", "Radius", arguments["radius"], "Rounded")


def chamfer_edges(arguments):
    return _apply_dressup("Chamfer", "Size", arguments["size"], "Chamfered")


def hole(arguments):
    """A real Part Design hole: a sketch of circles on a face, then the feature.

    Positions are in the sketch's own coordinates on that face, so (0, 0) is
    where the face's attachment origin lands.
    """
    import Part
    import Sketcher
    from FreeCAD import Vector

    faces = [(e.Object, n) for e in FreeCADGui.Selection.getSelectionEx()
             for n in e.SubElementNames if n.startswith("Face")]
    if not faces:
        return "No face is selected. Ask the user to click the face to drill into."

    owner, face_name = faces[0]
    body = _body(owner)
    if body is None:
        return "%s is not inside a Part Design body." % owner.Label

    diameter = arguments.get("diameter")
    thread = arguments.get("thread")
    if diameter is None and thread:
        diameter = CLEARANCE.get(str(thread).upper())
    if diameter is None:
        return "Say a diameter, or a thread size such as M4."

    positions = arguments.get("positions") or [{"x": 0, "y": 0}]

    sketch = body.newObject("Sketcher::SketchObject", "HoleSketch")
    sketch.AttachmentSupport = [(owner, face_name)]
    sketch.MapMode = "FlatFace"
    document().recompute()

    for position in positions:
        x = float(position.get("x", 0.0))
        y = float(position.get("y", 0.0))
        index = sketch.addGeometry(
            Part.Circle(Vector(x, y, 0), Vector(0, 0, 1), float(diameter) / 2.0), False)
        sketch.addConstraint(Sketcher.Constraint("Diameter", index, float(diameter)))
        sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, index, 3, x))
        sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, index, 3, y))

    feature = body.newObject("PartDesign::Hole", "Hole")
    feature.Profile = sketch
    feature.Diameter = float(diameter)

    if arguments.get("through_all", True):
        feature.DepthType = "ThroughAll"
        depth = "all the way through"
    else:
        feature.DepthType = "Dimension"
        feature.Depth = float(arguments["depth"])
        depth = "%s mm deep" % rounded(feature.Depth.Value)

    head = str(arguments.get("head", "none")).lower()
    if head in ("counterbore", "countersink"):
        feature.HoleCutType = head.capitalize()

    # A thread size on its own means a clearance hole for that bolt; tapping
    # it is a separate request.
    if thread and arguments.get("threaded"):
        feature.Threaded = True
        feature.ThreadType = "ISOMetricProfile"
        feature.ThreadSize = str(thread).upper()

    doc = document()
    doc.recompute()
    if "Invalid" in getattr(feature, "State", []):
        error = getattr(feature, "Error", "no reason given")
        doc.removeObject(feature.Name)
        doc.removeObject(sketch.Name)
        doc.recompute()
        return "That hole failed and was undone: %s" % error

    return "Drilled %d hole(s) of %s mm, %s, on %s as %s." % (
        len(positions), rounded(diameter), depth, face_name, feature.Name)


HANDLERS = {
    "fillet_edges": fillet_edges,
    "chamfer_edges": chamfer_edges,
    "hole": hole,
}
