"""Tools that only look at the document."""

import FreeCADGui

from ai_cad.util import body_of, document, find, rounded, solid_volume, vector

# Origin planes and axes are in every Body and only add noise.
NOISE = ("App::Origin", "App::Plane", "App::Line", "App::LocalCoordinateSystem")


def list_objects(_arguments):
    doc = document()
    if doc is None:
        return "No document is open. Use new_document to start one."

    lines = []
    for obj in doc.Objects:
        if obj.TypeId in NOISE:
            continue
        line = "%s (%s)" % (obj.Label, obj.TypeId)
        if obj.Label != obj.Name:
            line += " [internal name %s]" % obj.Name
        body = body_of(obj)
        if body is not None:
            line += " in %s" % body.Label
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


def _body_of(obj):
    """The Part Design body a feature belongs to, if any."""
    doc = document()
    if doc is None:
        return None
    for candidate in doc.Objects:
        if candidate.TypeId == "PartDesign::Body" and obj in candidate.Group:
            return candidate
    return None


def _standing(obj):
    """Where a feature sits in its body: the finished shape, or partway there.

    A feature in the middle of the tree has a shape of its own, and a volume
    that reads exactly like a finished part. Saying which is which here stops
    that number being quoted as the answer.
    """
    if not obj.isDerivedFrom("PartDesign::Feature"):
        return None
    body = _body_of(obj)
    tip = getattr(body, "Tip", None) if body is not None else None
    if tip is None:
        return None
    if tip is obj:
        return "This is the tip of %s: the finished shape of the part." % body.Label
    return ("CAREFUL: this is partway through %s, not the finished part. "
            "Everything above is this feature's own shape at this point in "
            "the tree. The finished shape is %s -- describe that one for the "
            "numbers to quote." % (body.Label, tip.Label))


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

    standing = _standing(obj)
    if standing:
        lines.append(standing)

    return "\n".join(lines)


# Below this an overlap is the boolean's own rounding, not material.
OVERLAP_NOISE = 1e-3    # mm3
TOUCHING = 1e-4         # mm


def _solid_for(name):
    """A whole part to test, from a body's name or anything inside one."""
    obj = find(name)
    if obj is None:
        return None, None, "There is no object called '%s'." % name
    if obj.TypeId != "PartDesign::Body":
        body = body_of(obj)
        if body is not None:
            obj = body
    if solid_volume(obj) <= 0:
        return None, None, "%s has no solid to test yet." % obj.Label
    return obj, obj.Shape, None


def check_interference(arguments):
    """Whether two parts overlap, touch, or clear each other -- and by how much.

    Both shapes are in model coordinates, body placement included, so this
    is the parts as they sit, not as they were drawn.
    """
    a, shape_a, error = _solid_for(arguments.get("body_a"))
    if error:
        return error
    b, shape_b, error = _solid_for(arguments.get("body_b"))
    if error:
        return error
    if a is b:
        return ("Both of those are %s -- one solid cannot collide with itself. "
                "Parts that must be checked against each other have to be "
                "separate bodies: see create_body." % a.Label)

    overlap = shape_a.common(shape_b)
    volume = overlap.Volume if not overlap.isNull() and overlap.Solids else 0.0
    if volume > OVERLAP_NOISE:
        box = overlap.BoundBox
        pieces = len(overlap.Solids)
        where = ("in one piece" if pieces == 1 else "in %d separate places" % pieces)
        return ("OVERLAPPING: %s and %s share %s mm3, %s. All of it lies "
                "inside x %s to %s, y %s to %s, z %s to %s (a box %s x %s x "
                "%s mm -- the overlap itself can be much thinner). As "
                "printed, these will not go together." % (
                    a.Label, b.Label, rounded(volume, 3), where,
                    rounded(box.XMin), rounded(box.XMax),
                    rounded(box.YMin), rounded(box.YMax),
                    rounded(box.ZMin), rounded(box.ZMax),
                    rounded(box.XLength), rounded(box.YLength), rounded(box.ZLength)))

    gap, pairs, _info = shape_a.distToShape(shape_b)
    near_a, near_b = pairs[0]
    if gap < TOUCHING:
        return ("TOUCHING, NO GAP: %s and %s meet at %s without overlapping. "
                "Drawn that way they fit exactly, which printed parts do not: "
                "if one slides into or sits against the other, give it "
                "clearance." % (a.Label, b.Label, vector(near_a)))
    return ("CLEAR: %s and %s do not touch. The smallest gap is %s mm, "
            "between %s on %s and %s on %s." % (
                a.Label, b.Label, rounded(gap, 3),
                vector(near_a), a.Label, vector(near_b), b.Label))


HANDLERS = {
    "check_interference": check_interference,
    "list_objects": list_objects,
    "describe_selection": describe_selection,
    "describe_object": describe_object,
}
