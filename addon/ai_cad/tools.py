"""The operations the model is allowed to perform.

Read-only so far: look at the document, the selection, and one object's size
and position. Steps 6 to 9 add the tools that change things.

Everything here runs on the GUI thread -- FreeCAD documents are not safe to
touch from a worker.
"""

import FreeCAD
import FreeCADGui

# Origin planes and axes are in every Body and only add noise.
NOISE = ("App::Origin", "App::Plane", "App::Line", "App::LocalCoordinateSystem")


def _document():
    return FreeCAD.ActiveDocument


def _round(value, places=2):
    return round(float(value), places)


def _vector(vec, places=2):
    return "(%s, %s, %s)" % (_round(vec.x, places), _round(vec.y, places), _round(vec.z, places))


def _find(name):
    """Objects can be addressed by internal name or by the label in the tree."""
    document = _document()
    if document is None:
        return None
    obj = document.getObject(name)
    if obj is not None:
        return obj
    matches = document.getObjectsByLabel(name)
    return matches[0] if matches else None


def list_objects(_arguments):
    document = _document()
    if document is None:
        return "No document is open."

    lines = []
    for obj in document.Objects:
        if obj.TypeId in NOISE:
            continue
        line = "%s (%s)" % (obj.Label, obj.TypeId)
        if obj.Label != obj.Name:
            line += " [internal name %s]" % obj.Name
        lines.append(line)

    if not lines:
        return "The document '%s' is open but has nothing in it." % document.Name
    return "Document '%s' contains:\n%s" % (document.Name, "\n".join(lines))


def _describe_subelement(shape):
    """A face, edge or vertex, in the terms the model will need to act on it."""
    kind = shape.ShapeType
    if kind == "Vertex":
        return "vertex at %s" % _vector(shape.Point)

    if kind == "Edge":
        curve = type(shape.Curve).__name__
        text = "%s edge, length %s mm, from %s to %s" % (
            curve.lower(), _round(shape.Length),
            _vector(shape.Vertexes[0].Point), _vector(shape.Vertexes[-1].Point))
        if curve == "Circle":
            text += ", radius %s mm, centre %s" % (
                _round(shape.Curve.Radius), _vector(shape.Curve.Center))
        return text

    if kind == "Face":
        surface = type(shape.Surface).__name__
        text = "%s face, area %s mm2" % (surface.lower(), _round(shape.Area))
        if surface == "Plane":
            text += ", normal %s" % _vector(shape.Surface.Axis)
        box = shape.BoundBox
        text += ", spans %s x %s x %s mm" % (
            _round(box.XLength), _round(box.YLength), _round(box.ZLength))
        return text

    return "%s" % kind.lower()


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

    obj = _find(name)
    if obj is None:
        return "There is no object called '%s'." % name

    lines = ["%s (%s)" % (obj.Label, obj.TypeId)]

    placement = getattr(obj, "Placement", None)
    if placement is not None:
        lines.append("position %s, rotation %s degrees about %s" % (
            _vector(placement.Base), _round(placement.Rotation.Angle * 57.2957795),
            _vector(placement.Rotation.Axis)))

    shape = getattr(obj, "Shape", None)
    if shape is not None and not shape.isNull():
        box = shape.BoundBox
        lines.append("bounding box %s x %s x %s mm" % (
            _round(box.XLength), _round(box.YLength), _round(box.ZLength)))
        lines.append("%d faces, %d edges" % (len(shape.Faces), len(shape.Edges)))
        if shape.Solids:
            lines.append("volume %s mm3" % _round(shape.Volume))

    # Whatever the feature itself is driven by: a pad's length, a box's sides.
    for prop in obj.PropertiesList:
        if obj.getTypeIdOfProperty(prop) in ("App::PropertyLength", "App::PropertyDistance"):
            lines.append("%s = %s mm" % (prop, _round(getattr(obj, prop).Value)))

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
                        "description": "The object's label as shown in the tree, or its internal name.",
                    },
                },
                "required": ["name"],
            },
        },
    },
]


def dispatch(name, arguments):
    handler = HANDLERS.get(name)
    if handler is None:
        return "There is no tool called %s." % name
    try:
        return handler(arguments)
    except Exception as exc:
        return "%s failed: %s: %s" % (name, type(exc).__name__, exc)
