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
