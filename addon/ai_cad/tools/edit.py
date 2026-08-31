"""Tools that change something that already exists, in place.

This is the difference between resizing a part and drawing a second one on
top of it. Constraints carry the user's intent, so changing the number in a
constraint is the right way to resize a sketch.
"""

import math

import FreeCAD

from ai_cad.util import document, find, rounded, vector

# Constraints that carry a number the user could sensibly change.
DIMENSIONAL = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle")

EDITABLE_PROPERTIES = (
    "App::PropertyLength", "App::PropertyDistance", "App::PropertyAngle",
    "App::PropertyFloat", "App::PropertyInteger", "App::PropertyBool",
    "App::PropertyEnumeration", "App::PropertyString",
)


def _sketch(name):
    sketch = find(name)
    if sketch is None:
        existing = [o.Label for o in (document().Objects if document() else [])
                    if o.TypeId == "Sketcher::SketchObject"]
        if not existing:
            return None, ("There is no sketch called '%s', and the document has "
                          "no sketches at all." % name)
        return None, "There is no sketch called '%s'. The sketches are: %s." % (
            name, ", ".join(existing))
    if sketch.TypeId != "Sketcher::SketchObject":
        return None, "'%s' is a %s, not a sketch." % (name, sketch.TypeId)
    return sketch, None


def list_constraints(arguments):
    """The numbers driving a sketch, so one of them can be changed."""
    sketch, error = _sketch(arguments.get("sketch"))
    if error:
        return error

    lines = []
    for index, constraint in enumerate(sketch.Constraints):
        if constraint.Type not in DIMENSIONAL:
            continue
        if constraint.Type == "Angle":
            value = "%s degrees" % rounded(math.degrees(constraint.Value))
        else:
            value = "%s mm" % rounded(constraint.Value)
        label = " named '%s'" % constraint.Name if constraint.Name else ""
        lines.append("%d: %s%s = %s" % (index, constraint.Type, label, value))

    if not lines:
        return "%s has no dimensional constraints." % sketch.Name
    return "Dimensions in %s:\n%s" % (sketch.Name, "\n".join(lines))


def set_dimension(arguments):
    """Change one constraint's value -- the proper way to resize a sketch."""
    sketch, error = _sketch(arguments.get("sketch"))
    if error:
        return error

    index = arguments.get("index")
    if index is None:
        return "Say which constraint to change, by index from list_constraints."
    index = int(index)
    if index < 0 or index >= len(sketch.Constraints):
        return "%s has constraints 0 to %d." % (sketch.Name, len(sketch.Constraints) - 1)

    constraint = sketch.Constraints[index]
    if constraint.Type not in DIMENSIONAL:
        return "Constraint %d is a %s -- it carries no number to change." % (
            index, constraint.Type)

    value = float(arguments["value"])
    sketch.setDatum(index, math.radians(value) if constraint.Type == "Angle" else value)
    document().recompute()

    unit = "degrees" if constraint.Type == "Angle" else "mm"
    return "%s constraint %d in %s is now %s %s." % (
        constraint.Type, index, sketch.Name, rounded(value), unit)


def set_property(arguments):
    """Change a feature's own number: a pad's length, a pocket's depth."""
    name = arguments.get("name")
    obj = find(name)
    if obj is None:
        return "There is no object called '%s'." % name

    prop = arguments.get("property")
    if prop not in obj.PropertiesList:
        editable = [p for p in obj.PropertiesList
                    if obj.getTypeIdOfProperty(p) in EDITABLE_PROPERTIES]
        return "%s has no property '%s'. It has: %s" % (
            obj.Label, prop, ", ".join(editable))

    kind = obj.getTypeIdOfProperty(prop)
    if kind not in EDITABLE_PROPERTIES:
        return "'%s' is a %s and cannot be set this way." % (prop, kind)

    raw = arguments.get("value")
    if kind == "App::PropertyBool":
        value = bool(raw) if not isinstance(raw, str) else raw.lower() in ("true", "yes", "1")
    elif kind in ("App::PropertyEnumeration", "App::PropertyString"):
        value = str(raw)
    elif kind == "App::PropertyInteger":
        value = int(raw)
    else:
        value = float(raw)

    setattr(obj, prop, value)
    document().recompute()
    return "%s.%s is now %s." % (obj.Label, prop, value)


def rename_object(arguments):
    obj = find(arguments.get("name"))
    if obj is None:
        return "There is no object called '%s'." % arguments.get("name")
    was = obj.Label
    obj.Label = str(arguments["new_name"])
    return "Renamed '%s' to '%s'." % (was, obj.Label)


def move_object(arguments):
    """Set where an object sits. Absolute unless relative is true."""
    obj = find(arguments.get("name"))
    if obj is None:
        return "There is no object called '%s'." % arguments.get("name")
    if not hasattr(obj, "Placement"):
        return "%s has no placement to move." % obj.Label

    offset = FreeCAD.Vector(
        float(arguments.get("x", 0.0)),
        float(arguments.get("y", 0.0)),
        float(arguments.get("z", 0.0)))

    placement = obj.Placement
    placement.Base = placement.Base + offset if arguments.get("relative") else offset
    obj.Placement = placement
    document().recompute()
    return "%s is now at %s." % (obj.Label, vector(obj.Placement.Base))


def rotate_object(arguments):
    """Rotate about one of the main axes, in degrees."""
    obj = find(arguments.get("name"))
    if obj is None:
        return "There is no object called '%s'." % arguments.get("name")
    if not hasattr(obj, "Placement"):
        return "%s has no placement to rotate." % obj.Label

    axes = {"X": FreeCAD.Vector(1, 0, 0),
            "Y": FreeCAD.Vector(0, 1, 0),
            "Z": FreeCAD.Vector(0, 0, 1)}
    axis = str(arguments.get("axis", "Z")).upper()
    if axis not in axes:
        return "Axis must be X, Y or Z."

    angle = float(arguments["angle"])
    rotation = FreeCAD.Rotation(axes[axis], angle)
    placement = obj.Placement
    placement.Rotation = rotation.multiply(placement.Rotation)
    obj.Placement = placement
    document().recompute()
    return "Rotated %s by %s degrees about %s." % (obj.Label, rounded(angle), axis)


def set_sketch_plane(arguments):
    """Move a sketch onto a different plane or onto the clicked face."""
    import FreeCADGui

    sketch, error = _sketch(arguments.get("sketch"))
    if error:
        return error

    planes = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}
    plane = str(arguments.get("plane", "XY")).upper()

    if plane == "SELECTION":
        faces = [(e.Object, n) for e in FreeCADGui.Selection.getSelectionEx()
                 for n in e.SubElementNames if n.startswith("Face")]
        if not faces:
            return "No face is selected."
        sketch.AttachmentSupport = [faces[0]]
        where = "%s of %s" % (faces[0][1], faces[0][0].Label)
    else:
        if plane not in planes:
            return "Plane must be XY, XZ, YZ or selection."
        body = sketch.getParent() if hasattr(sketch, "getParent") else None
        origins = [o for o in document().Objects
                   if o.Name.startswith(planes[plane]) and o.TypeId == "App::Plane"]
        if not origins:
            return "Could not find the %s plane." % plane
        sketch.AttachmentSupport = [(origins[0], "")]
        where = "the %s plane" % plane

    sketch.MapMode = "FlatFace"
    document().recompute()
    return "%s is now on %s." % (sketch.Name, where)


HANDLERS = {
    "list_constraints": list_constraints,
    "set_dimension": set_dimension,
    "set_property": set_property,
    "rename_object": rename_object,
    "move_object": move_object,
    "rotate_object": rotate_object,
    "set_sketch_plane": set_sketch_plane,
}


def _spec(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


SPECS = [
    _spec("list_constraints",
          "List the dimensional constraints driving a sketch, numbered. Use this "
          "before changing a size.",
          {"sketch": {"type": "string", "description": "Name of the sketch."}},
          ["sketch"]),
    _spec("set_dimension",
          "Change one constraint's value. This is how to resize something that "
          "is already drawn -- never draw a second shape to change a size.",
          {"sketch": {"type": "string", "description": "Name of the sketch."},
           "index": {"type": "integer", "description": "Constraint index from list_constraints."},
           "value": {"type": "number", "description": "New value, mm or degrees."}},
          ["sketch", "index", "value"]),
    _spec("set_property",
          "Change a feature's own value, such as a pad's Length or a pocket's "
          "Depth. Use describe_object to see what a feature has.",
          {"name": {"type": "string", "description": "The object's label or internal name."},
           "property": {"type": "string", "description": "Property name, e.g. Length."},
           "value": {"description": "The new value."}},
          ["name", "property", "value"]),
    _spec("rename_object",
          "Give an object a meaningful name in the tree.",
          {"name": {"type": "string", "description": "Current label or internal name."},
           "new_name": {"type": "string", "description": "The new label."}},
          ["name", "new_name"]),
    _spec("move_object",
          "Move an object. Absolute position by default; set relative to shift "
          "it from where it is.",
          {"name": {"type": "string", "description": "The object to move."},
           "x": {"type": "number", "description": "X in mm. Default 0."},
           "y": {"type": "number", "description": "Y in mm. Default 0."},
           "z": {"type": "number", "description": "Z in mm. Default 0."},
           "relative": {"type": "boolean", "description": "Shift rather than set. Default false."}},
          ["name"]),
    _spec("rotate_object",
          "Rotate an object about the X, Y or Z axis, in degrees.",
          {"name": {"type": "string", "description": "The object to rotate."},
           "axis": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Axis to turn about."},
           "angle": {"type": "number", "description": "Degrees."}},
          ["name", "angle"]),
    _spec("set_sketch_plane",
          "Re-attach a sketch to a different origin plane, or to the face the "
          "user has clicked.",
          {"sketch": {"type": "string", "description": "Name of the sketch."},
           "plane": {"type": "string", "enum": ["XY", "XZ", "YZ", "selection"],
                     "description": "Where to put it."}},
          ["sketch", "plane"]),
]
