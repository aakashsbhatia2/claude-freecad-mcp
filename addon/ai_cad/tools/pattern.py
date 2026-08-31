"""Repeating a feature: rows of holes, bolt circles, mirrored brackets."""

from ai_cad.util import document, find, rounded

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


def _feature_named(name):
    obj = find(name)
    if obj is None:
        return None, None, "There is no object called '%s'." % name
    body = _body_of(obj)
    if body is None:
        return None, None, "%s is not inside a Part Design body." % obj.Label
    return obj, body, None


def _finish(feature, doc, description):
    doc.recompute()
    if "Invalid" in getattr(feature, "State", []):
        error = getattr(feature, "Error", "no reason given")
        doc.removeObject(feature.Name)
        doc.recompute()
        return "That %s failed and was undone: %s" % (description, error)
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
    feature.Transformations = [obj]
    feature.Direction = (reference, [""])
    feature.Length = float(arguments["length"])
    feature.Occurrences = int(arguments["count"])
    feature.Reversed = bool(arguments.get("reversed", False))

    problem = _finish(feature, document(), "pattern")
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
    feature.Transformations = [obj]
    feature.Axis = (reference, [""])
    feature.Angle = float(arguments.get("angle", 360.0))
    feature.Occurrences = int(arguments["count"])

    problem = _finish(feature, document(), "pattern")
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
    feature.Transformations = [obj]
    feature.MirrorPlane = (reference, [""])

    problem = _finish(feature, document(), "mirror")
    if problem:
        return problem
    return "Mirrored %s across the %s plane." % (obj.Label, plane)


HANDLERS = {
    "linear_pattern": linear_pattern,
    "polar_pattern": polar_pattern,
    "mirror_feature": mirror_feature,
}

SPECS = [
    {
        "type": "function",
        "function": {
            "name": "linear_pattern",
            "description": (
                "Repeat a feature in a straight line, such as a row of holes. "
                "The length is the distance from the first copy to the last."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string", "description": "The feature to repeat, e.g. Hole."},
                    "direction": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Which way to go."},
                    "length": {"type": "number", "description": "Total span in mm."},
                    "count": {"type": "integer", "description": "How many copies in total, including the original."},
                    "reversed": {"type": "boolean", "description": "Go the other way. Default false."},
                },
                "required": ["feature", "length", "count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "polar_pattern",
            "description": "Repeat a feature around an axis, such as bolts on a circle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string", "description": "The feature to repeat."},
                    "axis": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Axis to turn about. Default Z."},
                    "angle": {"type": "number", "description": "Degrees to spread over. Default 360."},
                    "count": {"type": "integer", "description": "How many copies in total."},
                },
                "required": ["feature", "count"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mirror_feature",
            "description": "Make a mirrored copy of a feature across an origin plane.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string", "description": "The feature to mirror."},
                    "plane": {"type": "string", "enum": ["XY", "XZ", "YZ"], "description": "Mirror plane. Default YZ."},
                },
                "required": ["feature"],
            },
        },
    },
]
