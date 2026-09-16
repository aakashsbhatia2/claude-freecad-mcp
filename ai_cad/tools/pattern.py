"""Repeating a feature: rows of holes, bolt circles, mirrored brackets."""

from ai_cad.util import document, find, rounded, set_tip, why

AXES = {"X": "X_Axis", "Y": "Y_Axis", "Z": "Z_Axis"}
PLANES = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}


def _body_of(obj):
    if obj.TypeId == "PartDesign::Body":
        return obj
    for candidate in document().Objects:
        if candidate.TypeId == "PartDesign::Body" and obj in candidate.Group:
            return candidate
    return None


def _origin_feature(body, wanted):
    for feature in body.Origin.OriginFeatures:
        if feature.Name.startswith(wanted):
            return feature
    return None


# When FreeCAD declines to say why, all we can honestly do is point at the
# things worth checking. No guessing at a cause in the wording.
USUAL_CAUSE = ("Worth checking: that the copies still meet the rest of the "
               "solid, and that the count and spacing suit the size of the "
               "part. describe_object on the body's tip will show you where "
               "the part actually sits.")


def _already_repeated(obj):
    """Patterns and mirrors cannot themselves be patterned or mirrored.

    FreeCAD only transforms an additive or subtractive feature -- a pad or a
    pocket. Pointed at another pattern it builds the feature, fails on
    recompute and says so; catching it here says it before anything is made,
    and names the pad to use instead.
    """
    if not obj.isDerivedFrom("PartDesign::Transformed"):
        return None
    originals = [o.Label for o in getattr(obj, "Originals", [])]
    instead = (" Point this at %s instead, and fold the repeats you wanted "
               "into one pattern." % " and ".join(originals)) if originals else ""
    return ("%s is itself a pattern, and FreeCAD can only repeat or mirror a "
            "pad or a pocket -- not another pattern.%s" % (obj.Label, instead))


def _feature_named(name):
    obj = find(name)
    if obj is None:
        return None, None, "There is no object called '%s'." % name
    body = _body_of(obj)
    if body is None:
        return None, None, "%s is not inside a Part Design body." % obj.Label
    repeated = _already_repeated(obj)
    if repeated:
        return None, None, repeated
    return obj, body, None


def _finish(feature, body, doc, description):
    doc.recompute()
    if "Invalid" in getattr(feature, "State", []):
        reason = why(feature)
        doc.removeObject(feature.Name)
        doc.recompute()
        if reason:
            return "That %s failed and was undone: %s" % (description, reason)
        return "That %s failed and was undone. FreeCAD gave no reason. %s" % (
            description, USUAL_CAUSE)
    set_tip(body, feature)
    doc.recompute()
    return None


def linear_pattern(arguments):
    """Copies in a straight line -- a row of holes along an edge."""
    obj, body, error = _feature_named(arguments.get("feature"))
    if error:
        return error

    axis = str(arguments.get("direction", "X")).upper()
    if axis not in AXES:
        return "Direction must be X, Y or Z."
    reference = _origin_feature(body, AXES[axis])
    if reference is None:
        return "Could not find the %s axis." % axis

    feature = body.newObject("PartDesign::LinearPattern", "LinearPattern")
    feature.Originals = [obj]
    feature.Direction = (reference, [""])
    feature.Length = float(arguments["length"])
    feature.Occurrences = int(arguments["count"])
    feature.Reversed = bool(arguments.get("reversed", False))

    problem = _finish(feature, body, document(), "pattern")
    if problem:
        return problem
    return "Repeated %s %d times over %s mm along %s." % (
        obj.Label, feature.Occurrences, rounded(feature.Length.Value), axis)


def polar_pattern(arguments):
    """Copies around a circle -- a bolt pattern."""
    obj, body, error = _feature_named(arguments.get("feature"))
    if error:
        return error

    axis = str(arguments.get("axis", "Z")).upper()
    if axis not in AXES:
        return "Axis must be X, Y or Z."
    reference = _origin_feature(body, AXES[axis])
    if reference is None:
        return "Could not find the %s axis." % axis

    feature = body.newObject("PartDesign::PolarPattern", "PolarPattern")
    feature.Originals = [obj]
    feature.Axis = (reference, [""])
    feature.Angle = float(arguments.get("angle", 360.0))
    feature.Occurrences = int(arguments["count"])

    problem = _finish(feature, body, document(), "pattern")
    if problem:
        return problem
    return "Repeated %s %d times over %s degrees about %s." % (
        obj.Label, feature.Occurrences, rounded(feature.Angle.Value), axis)


def mirror_feature(arguments):
    """A mirrored copy across one of the origin planes."""
    obj, body, error = _feature_named(arguments.get("feature"))
    if error:
        return error

    plane = str(arguments.get("plane", "YZ")).upper()
    if plane not in PLANES:
        return "Plane must be XY, XZ or YZ."
    reference = _origin_feature(body, PLANES[plane])
    if reference is None:
        return "Could not find the %s plane." % plane

    feature = body.newObject("PartDesign::Mirrored", "Mirrored")
    feature.Originals = [obj]
    feature.MirrorPlane = (reference, [""])

    problem = _finish(feature, body, document(), "mirror")
    if problem:
        return problem
    return "Mirrored %s across the %s plane." % (obj.Label, plane)


HANDLERS = {
    "linear_pattern": linear_pattern,
    "polar_pattern": polar_pattern,
    "mirror_feature": mirror_feature,
}
