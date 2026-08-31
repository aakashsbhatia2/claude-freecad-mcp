"""Tools that only look at the document."""

import FreeCADGui

from ai_cad.util import document, find, rounded, vector

# Origin planes and axes are in every Body and only add noise.
NOISE = ("App::Origin", "App::Plane", "App::Line", "App::LocalCoordinateSystem")


def list_objects(_arguments):
    doc = document()
    if doc is None:
        return "No document is open."

    lines = []
    for obj in doc.Objects:
        if obj.TypeId in NOISE:
            continue
        line = "%s (%s)" % (obj.Label, obj.TypeId)
        if obj.Label != obj.Name:
            line += " [internal name %s]" % obj.Name
        lines.append(line)

    if not lines:
        return "The document '%s' is open but has nothing in it." % doc.Name
    return "Document '%s' contains:\n%s" % (doc.Name, "\n".join(lines))


def _describe_subelement(shape):
    """A face, edge or vertex, in the terms the model will need to act on it."""
    kind = shape.ShapeType
    if kind == "Vertex":
        return "vertex at %s" % vector(shape.Point)

    if kind == "Edge":
        curve = type(shape.Curve).__name__
        text = "%s edge, length %s mm, from %s to %s" % (
            curve.lower(), rounded(shape.Length),
            vector(shape.Vertexes[0].Point), vector(shape.Vertexes[-1].Point))
        if curve == "Circle":
            text += ", radius %s mm, centre %s" % (
                rounded(shape.Curve.Radius), vector(shape.Curve.Center))
        return text

    if kind == "Face":
        surface = type(shape.Surface).__name__
        text = "%s face, area %s mm2" % (surface.lower(), rounded(shape.Area))
        if surface == "Plane":
            text += ", normal %s" % vector(shape.Surface.Axis)
        box = shape.BoundBox
        text += ", spans %s x %s x %s mm" % (
            rounded(box.XLength), rounded(box.YLength), rounded(box.ZLength))
        return text

    return kind.lower()


def describe_selection(_arguments):
    selection = FreeCADGui.Selection.getSelectionEx()
    if not selection:
        return "Nothing is selected. Ask the user to click what they mean."

    lines = []
    for entry in selection:
        obj = entry.Object
        if not entry.SubElementNames:
            lines.append("%s (%s), whole object" % (obj.Label, obj.TypeId))
            continue
        for name, sub in zip(entry.SubElementNames, entry.SubObjects):
            lines.append("%s of %s: %s" % (name, obj.Label, _describe_subelement(sub)))
    return "\n".join(lines)


def describe_object(arguments):
    name = arguments.get("name")
    if not name:
        return "Say which object to describe."

    obj = find(name)
    if obj is None:
        return "There is no object called '%s'." % name

    lines = ["%s (%s)" % (obj.Label, obj.TypeId)]

    placement = getattr(obj, "Placement", None)
    if placement is not None:
        lines.append("position %s, rotation %s degrees about %s" % (
            vector(placement.Base), rounded(placement.Rotation.Angle * 57.2957795),
            vector(placement.Rotation.Axis)))

    shape = getattr(obj, "Shape", None)
    if shape is not None and not shape.isNull():
        box = shape.BoundBox
        lines.append("bounding box %s x %s x %s mm" % (
            rounded(box.XLength), rounded(box.YLength), rounded(box.ZLength)))
        lines.append("%d faces, %d edges" % (len(shape.Faces), len(shape.Edges)))
        if shape.Solids:
            lines.append("volume %s mm3" % rounded(shape.Volume))

    # Whatever the feature itself is driven by: a pad's length, a box's sides.
    for prop in obj.PropertiesList:
        if obj.getTypeIdOfProperty(prop) in ("App::PropertyLength", "App::PropertyDistance"):
            lines.append("%s = %s mm" % (prop, rounded(getattr(obj, prop).Value)))

    return "\n".join(lines)


HANDLERS = {
    "list_objects": list_objects,
    "describe_selection": describe_selection,
    "describe_object": describe_object,
}

SPECS = [
    {
        "type": "function",
        "function": {
            "name": "list_objects",
            "description": (
                "List everything in the open FreeCAD document: bodies, sketches "
                "and features, with their types. Use this first to see what exists."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_selection",
            "description": (
                "Describe what the user has currently clicked in the 3D view or "
                "the tree -- which faces, edges or objects, and their size and "
                "position. Use this whenever the user says 'this' or 'that'."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_object",
            "description": (
                "Report one object's dimensions, position and driving values, "
                "such as a pad's length or a box's sides."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The object's label in the tree, or its internal name.",
                    },
                },
                "required": ["name"],
            },
        },
    },
]
