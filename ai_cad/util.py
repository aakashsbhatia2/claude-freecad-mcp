"""Small helpers shared by the tool modules."""

import FreeCAD


def document():
    return FreeCAD.ActiveDocument


def rounded(value, places=2):
    return round(float(value), places)


def vector(vec, places=2):
    return "(%s, %s, %s)" % (
        rounded(vec.x, places), rounded(vec.y, places), rounded(vec.z, places))


def find(name):
    """Objects can be addressed by internal name or by the label in the tree."""
    doc = document()
    if doc is None or not name:
        return None
    obj = doc.getObject(name)
    if obj is not None:
        return obj
    matches = doc.getObjectsByLabel(name)
    return matches[0] if matches else None


def why(feature):
    """FreeCAD's own reason for refusing a feature, if it gave one.

    getStatusString carries the real message -- "Only additive and subtractive
    features can be transformed", say. The Error property that used to be read
    here does not exist on most features, which is how every failure came back
    as "no reason given".
    """
    for read in (lambda: feature.getStatusString(),
                 lambda: getattr(feature, "Error", "")):
        try:
            text = (read() or "").strip()
        except Exception:
            continue
        if text and text.lower() not in ("valid", "touched", "invalid"):
            return text
    return ""


def set_tip(body, feature):
    """Make a newly built feature the end of the body.

    Body.newObject advances the tip for a pad or a pocket but not for a
    pattern, a mirror or a dress-up. Left alone, the feature sits in the tree
    looking right and contributing nothing: the next pad chains onto the
    feature before it and the patterned copies vanish from the solid.
    """
    if body is not None and getattr(body, "Tip", None) is not feature:
        body.Tip = feature


def body_of(obj):
    """The Part Design body an object sits in, or None.

    Searched in the object's own document, which is not always the active one.
    """
    if obj is None:
        return None
    doc = obj.Document
    for candidate in doc.Objects:
        if candidate.TypeId == "PartDesign::Body" and obj in candidate.Group:
            return candidate
    return None


def solid_volume(obj):
    """Volume of an object's solid, or 0 when it has none."""
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull() or not shape.Solids:
        return 0.0
    return shape.Volume


AXES = (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)),
        ("-Y", (0, -1, 0)), ("+Z", (0, 0, 1)), ("-Z", (0, 0, -1)))


def direction(vec):
    """A world direction as +X, -Z and so on, or as numbers when it is neither."""
    for name, (x, y, z) in AXES:
        if abs(vec.x - x) < 1e-6 and abs(vec.y - y) < 1e-6 and abs(vec.z - z) < 1e-6:
            return name
    return vector(vec)


def facing(sketch):
    """The world direction a sketch faces -- the way a pad grows from it."""
    return sketch.getGlobalPlacement().Rotation.multVec(FreeCAD.Vector(0, 0, 1))


def orientation(sketch):
    """Where a sketch's own coordinates land in the model, in one sentence.

    A sketch on a clicked face has that face's axes, not the model's, and
    nothing drawn in it can be placed right without knowing them. Counterbores
    at (82.5, 5.5) landed off the part for exactly that reason.
    """
    placement = sketch.getGlobalPlacement()
    turn = placement.Rotation
    return ("Its (0, 0) is at %s in the model; its X runs along %s, its Y "
            "along %s, and it faces %s." % (
                vector(placement.Base),
                direction(turn.multVec(FreeCAD.Vector(1, 0, 0))),
                direction(turn.multVec(FreeCAD.Vector(0, 1, 0))),
                direction(turn.multVec(FreeCAD.Vector(0, 0, 1)))))


def remove_feature(obj):
    """Delete an object without breaking the body around it.

    doc.removeObject on its own leaves the next feature pointing at nothing,
    so everything before the gap drops out of the solid: a 20 x 20 x 10 block
    with a pocket and a pad on top came out at 125 mm3 instead of 4,125.
    Taking it out through the body first relinks the next feature and moves
    the tip back.
    """
    doc = obj.Document
    body = body_of(obj)
    if body is not None:
        body.removeObject(obj)
    doc.removeObject(obj.Name)
