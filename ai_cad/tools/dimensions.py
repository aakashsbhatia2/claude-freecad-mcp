"""Putting the model's own numbers on the model, where they can be looked at.

Every driving dimension already exists as a sketch constraint or a feature's
length. This writes each one into the 3D view as a real dimension line, or as
text where a line would mean nothing -- a diameter, an angle. They are
ordinary objects holding plain points, so nothing here can drift when
FreeCAD renumbers a face, and nothing here changes the solid, the mesh or
what gets exported.
"""

import math

import FreeCAD

from FreeCAD import Vector

from ai_cad.util import body_of, document, find, rounded

GROUP = "Dimensions"

# Constraints that carry a number worth showing, and how to show it.
SPANS = ("Distance", "DistanceX", "DistanceY")
NOTES = {"Radius": "R%s mm", "Diameter": "%s mm diameter", "Angle": "%s degrees"}

# Where a constraint's endpoint sits on a piece of geometry.
START, END, CENTRE = 1, 2, 3


def _point(sketch, geo, pos):
    """One end of one constraint, in the sketch's own flat coordinates."""
    if geo is None or geo == -2000:
        return None
    if geo < 0:                       # the origin and the two sketch axes
        return Vector(0, 0, 0) if pos == START else None
    try:
        element = sketch.Geometry[geo]
    except IndexError:
        return None

    if pos == START and hasattr(element, "StartPoint"):
        return element.StartPoint
    if pos == END and hasattr(element, "EndPoint"):
        return element.EndPoint
    if pos == CENTRE and hasattr(element, "Center"):
        return element.Center
    if hasattr(element, "Center"):    # a whole circle or arc
        return element.Center
    if hasattr(element, "StartPoint"):
        return (element.StartPoint + element.EndPoint) * 0.5
    return None


def _flatten(kind, first, second):
    """Keep a DistanceX or DistanceY line along the axis it measures.

    Drawn corner to corner it would read as the diagonal, which is not the
    number the constraint holds.
    """
    if kind == "DistanceX":
        return Vector(second.x, first.y, 0)
    if kind == "DistanceY":
        return Vector(first.x, second.y, 0)
    return second


class _Sheet(object):
    """Collects the dimensions for one sketch into its own group."""

    def __init__(self, doc, parent, label):
        self.doc = doc
        self.group = doc.addObject("App::DocumentObjectGroup", "Dims")
        self.group.Label = "dims %s" % label
        parent.addObject(self.group)
        self.count = 0

    def line(self, label, start, end):
        measure = self.doc.addObject("Measure::MeasureDistanceDetached", "Dim")
        measure.Position1 = start
        measure.Position2 = end
        measure.Label = label
        self.group.addObject(measure)
        self.count += 1

    def note(self, label, at):
        text = self.doc.addObject("App::Annotation", "Note")
        text.LabelText = [label]
        text.Position = at
        text.Label = label
        self.group.addObject(text)
        self.count += 1


def _mark_sketch(sketch, doc, parent):
    """Every dimensional constraint in one sketch, in model coordinates."""
    sheet = _Sheet(doc, parent, sketch.Label)
    placement = sketch.getGlobalPlacement()

    for index, constraint in enumerate(sketch.Constraints):
        kind = constraint.Type
        name = "%s [%d] " % (sketch.Label, index)

        if kind in SPANS:
            first = _point(sketch, constraint.First, constraint.FirstPos)
            second = _point(sketch, constraint.Second, constraint.SecondPos)
            if first is None:
                continue
            if second is None:        # a length measured from the sketch origin
                second = Vector(0, 0, 0)
                first, second = second, first
            second = _flatten(kind, first, second)
            if (second - first).Length < 1e-9:
                continue
            sheet.line(name + "%s mm" % rounded(constraint.Value),
                       placement.multVec(first), placement.multVec(second))

        elif kind in NOTES:
            at = _point(sketch, constraint.First, constraint.FirstPos)
            if at is None:
                continue
            value = math.degrees(constraint.Value) if kind == "Angle" else constraint.Value
            sheet.note(name + NOTES[kind] % rounded(value), placement.multVec(at))

    return sheet


def _profile(feature):
    link = getattr(feature, "Profile", None)
    if isinstance(link, tuple):
        link = link[0] if link else None
    return link


def _mark_length(feature, sheet):
    """How far a pad grew, or a pocket cut, drawn along the way it went."""
    sketch = _profile(feature)
    length = getattr(feature, "Length", None)
    if sketch is None or length is None or not length.Value:
        return
    shape = getattr(sketch, "Shape", None)
    if shape is None or shape.isNull():
        return

    turn = sketch.getGlobalPlacement().Rotation
    way = turn.multVec(Vector(0, 0, 1))
    if feature.TypeId == "PartDesign::Pocket":
        way = -way
    if getattr(feature, "Reversed", False):
        way = -way

    start = shape.BoundBox.Center
    sheet.line("%s %s mm" % (feature.Label, rounded(length.Value)),
               start, start + way * length.Value)


def _in_scope(arguments, doc):
    """The sketches to mark: one, one body's worth, or the whole document."""
    if arguments.get("sketch"):
        sketch = find(arguments["sketch"])
        if sketch is None or sketch.TypeId != "Sketcher::SketchObject":
            return None, "There is no sketch called '%s'." % arguments["sketch"]
        return [sketch], None

    sketches = [o for o in doc.Objects if o.TypeId == "Sketcher::SketchObject"]
    if arguments.get("body"):
        body = find(arguments["body"])
        if body is None or body.TypeId != "PartDesign::Body":
            return None, "There is no body called '%s'." % arguments["body"]
        sketches = [s for s in sketches if body_of(s) is body]
    if not sketches:
        return None, "There are no sketches to take dimensions from."
    return sketches, None


def _existing(doc):
    for obj in doc.Objects:
        if obj.TypeId == "App::DocumentObjectGroup" and obj.Label == GROUP:
            return obj
    return None


def _remove_group(group, doc):
    for member in list(group.Group):
        for inner in list(getattr(member, "Group", [])):
            doc.removeObject(inner.Name)
        doc.removeObject(member.Name)
    doc.removeObject(group.Name)


def mark_dimensions(arguments):
    """Show every driving number of the model in the 3D view."""
    doc = document()
    if doc is None:
        return "No document is open."
    sketches, error = _in_scope(arguments, doc)
    if error:
        return error

    old = _existing(doc)
    if old is not None:
        _remove_group(old, doc)       # marking again replaces, never stacks

    parent = doc.addObject("App::DocumentObjectGroup", "Dimensions")
    parent.Label = GROUP

    total = 0
    sheets = []
    for sketch in sketches:
        sheet = _mark_sketch(sketch, doc, parent)
        for feature in doc.Objects:
            if _profile(feature) is sketch:
                _mark_length(feature, sheet)
        total += sheet.count
        sheets.append("%s (%d)" % (sketch.Label, sheet.count))

    doc.recompute()
    if not total:
        _remove_group(parent, doc)
        doc.recompute()
        return "Nothing to mark: none of those sketches carries a dimension."
    return ("Marked %d dimensions in the 3D view, in a '%s' group -- one "
            "sub-group per sketch, so you can switch them on one at a time: "
            "%s. Each is named for the sketch and the constraint number "
            "behind it, so a wrong number says what to change. "
            "clear_dimensions takes them all away again." % (
                total, GROUP, ", ".join(sheets)))


def clear_dimensions(_arguments):
    doc = document()
    if doc is None:
        return "No document is open."
    group = _existing(doc)
    if group is None:
        return "There are no dimension marks to clear."
    _remove_group(group, doc)
    doc.recompute()
    return "Cleared the dimension marks."


HANDLERS = {
    "mark_dimensions": mark_dimensions,
    "clear_dimensions": clear_dimensions,
}
