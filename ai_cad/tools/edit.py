"""Tools that change something that already exists, in place.

This is the difference between resizing a part and drawing a second one on
top of it. Constraints carry the user's intent, so changing the number in a
constraint is the right way to resize a sketch.
"""

import math

import FreeCAD

from ai_cad.util import document, find, orientation, rounded, vector

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


def set_dimension(arguments):
    """Change one constraint's value -- the proper way to resize a sketch."""
    sketch, error = _sketch(arguments.get("sketch"))
    if error:
        return error

    index = arguments.get("index")
    if index is None:
        return "Say which constraint to change, by index from describe_sketch."
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


def _driven_elsewhere(obj):
    """Why setting this object's placement would be thrown away, if it would.

    A Part Design feature takes its position from the body it is in, and an
    attached sketch from the plane or face it is on. FreeCAD accepts the
    assignment either way and overwrites it on the next recompute, so the old
    behaviour was to report a move that never happened.
    """
    if obj.isDerivedFrom("PartDesign::Feature"):
        return ("%s is a Part Design feature, so its position comes from the "
                "body and from the sketch it was made from -- setting it here "
                "would be undone on the next recompute. Move the sketch "
                "instead, or give the sketch an offset with set_sketch_plane, "
                "or move the whole body." % obj.Label)
    if (obj.TypeId == "Sketcher::SketchObject"
            and getattr(obj, "MapMode", "Deactivated") != "Deactivated"):
        return ("%s is attached to a plane or face, so its position is worked "
                "out from that and setting it here would be undone. Use "
                "set_sketch_plane with an offset to move it off that plane."
                % obj.Label)
    return None


def move_object(arguments):
    """Set where an object sits. Absolute unless relative is true."""
    obj = find(arguments.get("name"))
    if obj is None:
        return "There is no object called '%s'." % arguments.get("name")
    if not hasattr(obj, "Placement"):
        return "%s has no placement to move." % obj.Label
    refusal = _driven_elsewhere(obj)
    if refusal:
        return refusal

    offset = FreeCAD.Vector(
        float(arguments.get("x", 0.0)),
        float(arguments.get("y", 0.0)),
        float(arguments.get("z", 0.0)))

    placement = obj.Placement
    wanted = placement.Base + offset if arguments.get("relative") else offset
    placement.Base = wanted
    obj.Placement = placement
    document().recompute()

    # Belt and braces: say so if FreeCAD quietly put it back.
    landed = obj.Placement.Base
    if landed.distanceToPoint(wanted) > 1e-6:
        return ("%s did not move. It was asked for %s and is still at %s, so "
                "something else is driving its position." % (
                    obj.Label, vector(wanted), vector(landed)))
    return "%s is now at %s." % (obj.Label, vector(landed))


def rotate_object(arguments):
    """Rotate about one of the main axes, in degrees."""
    obj = find(arguments.get("name"))
    if obj is None:
        return "There is no object called '%s'." % arguments.get("name")
    if not hasattr(obj, "Placement"):
        return "%s has no placement to rotate." % obj.Label
    refusal = _driven_elsewhere(obj)
    if refusal:
        return refusal

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
    offset = float(arguments.get("offset") or 0.0)
    sketch.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0, 0, offset), FreeCAD.Rotation())
    document().recompute()

    where = "%s mm off %s" % (rounded(offset), where) if offset else "on " + where
    return "%s is now %s. %s" % (sketch.Label, where, orientation(sketch))


HANDLERS = {
    "set_dimension": set_dimension,
    "set_property": set_property,
    "rename_object": rename_object,
    "move_object": move_object,
    "rotate_object": rotate_object,
    "set_sketch_plane": set_sketch_plane,
}
