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
