"""Tools that change the document: sketches, geometry, pads and pockets.

Everything is made the way Part Design makes it by hand -- a Body, a sketch
attached to a plane or a face, fully constrained geometry, then a pad or a
pocket driven by that sketch. The result is a normal parametric feature the
user can open and re-dimension.
"""

import math

import FreeCAD
import FreeCADGui
import Part
import Sketcher

from FreeCAD import Vector

from ai_cad.util import (body_of, direction, document, facing, find,
                         orientation, remove_feature, rounded, solid_volume)

PLANES = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}


def _require_document():
    doc = document()
    if doc is None:
        doc = FreeCAD.newDocument("Unnamed")
    return doc


def _bodies(doc):
    return [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]


def _gui_active_body():
    gui = FreeCADGui.ActiveDocument
    return gui.ActiveView.getActiveObject("pdbody") if gui is not None else None


def _make_active(body):
    """Show the body as active in FreeCAD, so the tree matches what we did."""
    gui = FreeCADGui.getDocument(body.Document.Name)
    if gui is not None and gui.ActiveView is not None:
        gui.ActiveView.setActiveObject("pdbody", body)


def _active_body(doc):
    """The body new features go into, creating one on first use.

    Returns (body, None), or (None, reason) when there are several bodies and
    none is marked active -- guessing there puts a sketch in the wrong part.
    """
    body = _gui_active_body()
    if body is not None and body.Document is doc:
        return body, None

    bodies = _bodies(doc)
    if len(bodies) > 1:
        return None, ("'%s' has several bodies and none is active: %s. Say "
                      "which one with body." % (
                          doc.Label, ", ".join(b.Label for b in bodies)))
    body = bodies[0] if bodies else doc.addObject("PartDesign::Body", "Body")
    _make_active(body)
    return body, None


def _body_named(doc, name):
    obj = find(name)
    if obj is None or obj.TypeId != "PartDesign::Body":
        bodies = _bodies(doc)
        listed = ", ".join(b.Label for b in bodies) if bodies else "none yet"
        return None, "There is no body called '%s'. The bodies are: %s." % (name, listed)
    return obj, None


def _body_of_sketch(sketch):
    """A feature goes in the body its sketch is in, not whichever is active."""
    body = body_of(sketch)
    if body is None:
        return None, "%s is not inside a body." % sketch.Label
    return body, None


def create_body(arguments):
    """A separate solid: a second part, a nut, anything that must not fuse."""
    doc = _require_document()
    body = doc.addObject("PartDesign::Body", "Body")
    if arguments.get("name"):
        body.Label = str(arguments["name"])
    _make_active(body)
    doc.recompute()
    others = [b.Label for b in _bodies(doc) if b is not body]
    text = "Created body '%s'. It is the active body now" % body.Label
    if others:
        text += ", separate from %s" % ", ".join(others)
    return text + ". Pass body='%s' to create_sketch to draw in it." % body.Label


def _origin_plane(body, plane):
    wanted = PLANES[plane]
    for feature in body.Origin.OriginFeatures:
        if feature.Name.startswith(wanted):
            return feature
    return None


def _sketch_names():
    doc = document()
    if doc is None:
        return []
    return [o.Label for o in doc.Objects if o.TypeId == "Sketcher::SketchObject"]


def _sketch_named(name):
    sketch = find(name)
    if sketch is None:
        existing = _sketch_names()
        if not existing:
            return None, ("There is no sketch called '%s', and the document has "
                          "no sketches at all. Use create_sketch first." % name)
        return None, "There is no sketch called '%s'. The sketches are: %s." % (
            name, ", ".join(existing))
    if sketch.TypeId != "Sketcher::SketchObject":
        return None, "'%s' is a %s, not a sketch." % (name, sketch.TypeId)
    return sketch, None


def _report(obj, doc):
    """Recompute and say whether the feature came out valid."""
    doc.recompute()
    if getattr(obj, "State", None) and "Invalid" in obj.State:
        return "%s was created but is invalid: %s" % (
            obj.Label, getattr(obj, "Error", "no reason given"))
    return None


def _offset_sketch(sketch, distance):
    """Lift a sketch off the plane it is attached to, along that plane's normal.

    This is what lets a wall 141 mm from the origin be drawn directly. Local Z
    is the normal of whatever the sketch is attached to, so one number moves it
    the only way that makes sense, and the caller reports where it landed
    rather than claiming which world axis that was.
    """
    sketch.AttachmentOffset = FreeCAD.Placement(
        Vector(0, 0, distance), FreeCAD.Rotation())


def create_sketch(arguments):
    """Start a sketch on an origin plane, or on the face the user has clicked."""
    plane = (arguments.get("plane") or "XY").upper()
    doc = _require_document()
    faces = []
    if plane == "SELECTION":
        selection = FreeCADGui.Selection.getSelectionEx()
        faces = [(e.Object, n) for e in selection for n in e.SubElementNames
                 if n.startswith("Face")]
        if not faces:
            return "No face is selected. Ask the user to click the face to sketch on."

    if arguments.get("body"):
        body, error = _body_named(doc, arguments["body"])
    elif faces and body_of(faces[0][0]) is not None:
        # A sketch can only sit on a face of its own body.
        body, error = body_of(faces[0][0]), None
    else:
        body, error = _active_body(doc)
    if error:
        return error
    _make_active(body)

    if faces:
        owner = body_of(faces[0][0])
        if owner is not None and owner is not body:
            return ("That face belongs to %s, and a sketch in %s cannot sit on "
                    "it. Use an origin plane with an offset instead." % (
                        owner.Label, body.Label))
        support = [faces[0]]
        where = "%s of %s" % (faces[0][1], faces[0][0].Label)
    else:
        if plane not in PLANES:
            return "Plane must be XY, XZ, YZ or selection."
        origin = _origin_plane(body, plane)
        if origin is None:
            return "Could not find the %s plane in %s." % (plane, body.Label)
        support = [(origin, "")]
        where = "the %s plane" % plane

    sketch = body.newObject("Sketcher::SketchObject", "Sketch")
    sketch.AttachmentSupport = support
    sketch.MapMode = "FlatFace"
    offset = float(arguments.get("offset") or 0.0)
    if offset:
        _offset_sketch(sketch, offset)
    if arguments.get("name"):
        sketch.Label = str(arguments["name"])
    doc.recompute()

    text = "Created an empty sketch on %s in body %s" % (where, body.Label)
    if offset:
        text += ", %s mm off it" % rounded(offset)
    return "%s. %s Call it '%s' from now on." % (
        text, orientation(sketch), sketch.Label)


def add_rectangle(arguments):
    """Four lines, fully constrained, centred on the given point."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    width = float(arguments["width"])
    height = float(arguments["height"])
    cx = float(arguments.get("center_x", 0.0))
    cy = float(arguments.get("center_y", 0.0))

    half_w, half_h = width / 2.0, height / 2.0
    corners = [
        Vector(cx - half_w, cy - half_h, 0),
        Vector(cx + half_w, cy - half_h, 0),
        Vector(cx + half_w, cy + half_h, 0),
        Vector(cx - half_w, cy + half_h, 0),
    ]

    first = sketch.GeometryCount
    for index in range(4):
        sketch.addGeometry(
            Part.LineSegment(corners[index], corners[(index + 1) % 4]), False)

    lines = [first + i for i in range(4)]
    for index in range(4):
        # End of each line meets the start of the next.
        sketch.addConstraint(Sketcher.Constraint(
            "Coincident", lines[index], 2, lines[(index + 1) % 4], 1))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", lines[0]))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", lines[2]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", lines[1]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", lines[3]))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", lines[0], 1, lines[0], 2, width))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", lines[1], 1, lines[1], 2, height))
    # Pinning one corner to the origin fixes where the rectangle sits.
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, lines[0], 1, cx - half_w))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, lines[0], 1, cy - half_h))

    document().recompute()
    return "Added a %s x %s mm rectangle to %s, centred on (%s, %s). %s" % (
        rounded(width), rounded(height), sketch.Name, rounded(cx), rounded(cy),
        _constraint_state(sketch))


def _constraint_state(sketch):
    """Whether the sketch is pinned down, in the words the user would use."""
    if getattr(sketch, "FullyConstrained", False):
        return "Fully constrained."
    freedom = getattr(sketch, "DoF", None)
    if freedom is None:
        return "Not fully constrained yet."
    return "Not fully constrained: %d degree(s) of freedom left." % freedom


def add_circle(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    diameter = float(arguments["diameter"])
    cx = float(arguments.get("center_x", 0.0))
    cy = float(arguments.get("center_y", 0.0))

    index = sketch.addGeometry(
        Part.Circle(Vector(cx, cy, 0), Vector(0, 0, 1), diameter / 2.0), False)
    sketch.addConstraint(Sketcher.Constraint("Diameter", index, diameter))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, index, 3, cx))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, index, 3, cy))

    document().recompute()
    return "Added a %s mm circle to %s, centred on (%s, %s). %s" % (
        rounded(diameter), sketch.Name, rounded(cx), rounded(cy),
        _constraint_state(sketch))


def _set_symmetric(feature, symmetric):
    """Grow the pad both ways from the sketch, or only one.

    FreeCAD 1.1 replaced Midplane with SideType and warns that Midplane is
    going away; FreeCAD 1.0 has only Midplane. Set whichever this one knows,
    so the add-on keeps working on both.
    """
    if hasattr(feature, "SideType"):
        feature.SideType = "Symmetric" if symmetric else "One side"
    else:
        feature.Midplane = symmetric


def pad(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error
    if sketch.GeometryCount == 0:
        return "%s is empty -- draw something in it first." % sketch.Name

    doc = document()
    body, error = _body_of_sketch(sketch)
    if error:
        return error
    feature = body.newObject("PartDesign::Pad", "Pad")
    feature.Profile = sketch
    feature.Length = float(arguments["length"])
    _set_symmetric(feature, bool(arguments.get("symmetric", False)))
    feature.Reversed = bool(arguments.get("reversed", False))

    problem = _report(feature, doc)
    if problem:
        return problem
    return "Padded %s by %s mm as %s, in %s." % (
        sketch.Label, rounded(feature.Length.Value), feature.Name, body.Label)


def pocket(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error
    if sketch.GeometryCount == 0:
        return "%s is empty -- draw something in it first." % sketch.Name

    doc = document()
    body, error = _body_of_sketch(sketch)
    if error:
        return error
    before = solid_volume(body.Tip) if body.Tip is not None else 0.0
    if before <= 0:
        return "%s has no solid yet, so there is nothing to cut into." % body.Label

    feature = body.newObject("PartDesign::Pocket", "Pocket")
    feature.Profile = sketch
    feature.Reversed = bool(arguments.get("reversed", False))

    if arguments.get("through_all"):
        feature.Type = 1  # ThroughAll
        depth = "all the way through"
    else:
        feature.Length = float(arguments["depth"])
        depth = "%s mm deep" % rounded(feature.Length.Value)

    problem = _report(feature, doc)
    if problem:
        return problem

    # A pocket cuts against the way its sketch faces; reversed cuts with it.
    way = facing(sketch)
    toward = direction(way if feature.Reversed else -way)
    removed = before - solid_volume(feature)

    if removed < 1e-6:
        remove_feature(feature)
        doc.recompute()
        return ("That pocket removed nothing, so it was taken out again. It cut "
                "%s towards %s, and there is no material that way from %s. "
                "Call pocket again with reversed set the other way, or move the "
                "sketch onto the part with an offset. %s" % (
                    depth, toward, sketch.Label, orientation(sketch)))

    return "Cut %s %s towards %s, removing %s mm3, as %s, in %s." % (
        sketch.Label, depth, toward, rounded(removed), feature.Name, body.Label)


# Where a constraint's endpoint sits on the geometry it names.
POINT_NAMES = {1: "start", 2: "end", 3: "centre"}

# Constraints carrying a number, and the unit that number is in. Radius and
# Diameter read backwards in that shape, so they are worded separately below.
MEASURED = {"Distance": "mm", "DistanceX": "mm in X", "DistanceY": "mm in Y",
            "Angle": "degrees"}
SIZED = {"Radius": "radius", "Diameter": "diameter"}


def _where(geo, pos):
    """Name one end of one element, the way a person would point at it."""
    if geo == -1:
        return "the origin" if pos == 1 else "the X axis"
    if geo == -2:
        return "the Y axis"
    point = POINT_NAMES.get(pos)
    return "%s of %d" % (point, geo) if point else "%d" % geo


def _constraint_text(constraint):
    """One constraint in a sentence, not a row of field names."""
    kind = constraint.Type
    first = _where(constraint.First, constraint.FirstPos)
    has_second = constraint.Second not in (None, -2000)
    second = _where(constraint.Second, constraint.SecondPos) if has_second else None

    if kind in SIZED:
        text = "%s has %s %s mm" % (first, SIZED[kind], rounded(constraint.Value))
    elif kind in MEASURED:
        value = math.degrees(constraint.Value) if kind == "Angle" else constraint.Value
        text = "%s %s" % (rounded(value), MEASURED[kind])
        text += " from %s to %s" % (first, second) if second else " on %s" % first
    elif kind == "Coincident":
        text = "%s meets %s" % (first, second)
    elif kind in ("Horizontal", "Vertical"):
        text = "%s is %s" % (first, kind.lower())
    elif second:
        text = "%s is %s to %s" % (first, kind.lower(), second)
    else:
        text = "%s is %s" % (first, kind.lower())

    if not constraint.Driving:
        text += " (reference only, drives nothing)"
    return text


def _geometry_text(geometry):
    """One drawn element, with the numbers needed to recognise it."""
    kind = type(geometry).__name__
    if kind == "LineSegment":
        return "line from (%s, %s) to (%s, %s)" % (
            rounded(geometry.StartPoint.x), rounded(geometry.StartPoint.y),
            rounded(geometry.EndPoint.x), rounded(geometry.EndPoint.y))
    if kind == "Circle":
        return "circle, diameter %s mm, centred on (%s, %s)" % (
            rounded(geometry.Radius * 2),
            rounded(geometry.Center.x), rounded(geometry.Center.y))
    if kind == "ArcOfCircle":
        return "arc, radius %s mm, centred on (%s, %s), %s to %s degrees" % (
            rounded(geometry.Radius),
            rounded(geometry.Center.x), rounded(geometry.Center.y),
            rounded(math.degrees(geometry.FirstParameter)),
            rounded(math.degrees(geometry.LastParameter)))
    if kind == "Point":
        return "point at (%s, %s)" % (
            rounded(geometry.X), rounded(geometry.Y))
    return kind.lower()


def _attached_to(sketch):
    """The plane or face the sketch is drawn on."""
    support = getattr(sketch, "AttachmentSupport", None)
    if not support:
        return "nothing"
    obj, subs = support[0]
    sub = subs[0] if subs and subs[0] else ""
    name = obj.Label.replace("_", " ") if not sub else "%s of %s" % (sub, obj.Label)
    return name


def describe_sketch(arguments):
    """Everything about one sketch in a single answer.

    Geometry and the constraints holding it are the same question -- asked
    apart, the model acts on half a picture. Each constraint is printed under
    every element it touches, so 'which one drives the width' is readable
    rather than guessed at, and its index is the one set_dimension wants.
    """
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error
    if sketch.GeometryCount == 0:
        return "%s is empty, on %s." % (sketch.Label, _attached_to(sketch))

    # Constraint indices gathered per element, so each is shown where it bites.
    attached = {}
    loose = []
    for index, constraint in enumerate(sketch.Constraints):
        touched = {g for g in (constraint.First, constraint.Second, constraint.Third)
                   if g is not None and g >= 0}
        if not touched:
            loose.append("  [%d] %s" % (index, _constraint_text(constraint)))
        for geo in touched:
            attached.setdefault(geo, []).append(
                "     [%d] %s" % (index, _constraint_text(constraint)))

    lines = []
    for index, geometry in enumerate(sketch.Geometry):
        construction = " (construction)" if sketch.getConstruction(index) else ""
        lines.append("%d: %s%s" % (index, _geometry_text(geometry), construction))
        lines.extend(attached.get(index, ["     nothing holds it in place"]))

    if loose:
        lines.append("Not tied to any element:")
        lines.extend(loose)

    return "%s, drawn on %s. %s\n\n%s" % (
        sketch.Label, _attached_to(sketch), _constraint_state(sketch),
        "\n".join(lines))


def delete_geometry(arguments):
    """Remove drawn elements from a sketch. A rectangle is four lines."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    indices = arguments.get("indices")
    if isinstance(indices, (int, float)):
        indices = [indices]
    if not indices:
        return "Say which elements to delete, by their index from describe_sketch."

    indices = sorted({int(i) for i in indices}, reverse=True)
    out_of_range = [i for i in indices if i < 0 or i >= sketch.GeometryCount]
    if out_of_range:
        return "%s only has elements 0 to %d; asked for %s." % (
            sketch.Name, sketch.GeometryCount - 1, out_of_range)

    # Deleting shifts the indices below, so go from the end backwards. Any
    # constraints attached to the geometry go with it.
    sketch.delGeometries(indices)
    document().recompute()
    return "Deleted %d element(s) from %s. %s" % (
        len(indices), sketch.Name, _constraint_state(sketch))


def _profile_of(obj):
    """The sketch a pad, pocket or hole was made from, if it has one."""
    link = getattr(obj, "Profile", None)
    if isinstance(link, tuple):
        link = link[0] if link else None
    if link is not None and link.TypeId == "Sketcher::SketchObject":
        return link
    return None


def _users(sketch):
    """Features built from a sketch. The body lists it too, but only as a member."""
    return [o for o in sketch.InList if o.TypeId != "PartDesign::Body"]


def delete_object(arguments):
    """Remove a sketch, pad or pocket without breaking the rest of the body."""
    name = arguments.get("name")
    obj = find(name)
    if obj is None:
        return "There is no object called '%s'." % name

    if obj.TypeId == "Sketcher::SketchObject":
        users = _users(obj)
        if users:
            return ("%s is what %s is made from, so deleting it would break "
                    "that. Delete %s instead -- its sketch goes with it." % (
                        obj.Label, ", ".join(u.Label for u in users),
                        " and ".join(u.Label for u in users)))

    doc = document()
    label = obj.Label
    body = body_of(obj)
    profile = _profile_of(obj)

    remove_feature(obj)
    gone = [label]
    # Left behind, a sketch with nothing built from it hangs in space in the
    # 3D view -- the "random circles floating" -- so it goes too.
    if profile is not None and not _users(profile):
        gone.append(profile.Label)
        remove_feature(profile)
    doc.recompute()

    text = "Deleted %s." % " and its sketch ".join(gone)
    if body is not None:
        broken = [o.Label for o in body.Group
                  if "Invalid" in getattr(o, "State", [])]
        if broken:
            text += " These no longer work and need looking at: %s." % ", ".join(broken)
        if body.Tip is not None:
            text += " %s now ends at %s." % (body.Label, body.Tip.Label)
    return text


def _pin_point(sketch, geo, pos, x, y):
    """Fix one endpoint in place, in the sketch's own coordinates."""
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, geo, pos, x))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, geo, pos, y))


def add_line(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    x1, y1 = float(arguments["x1"]), float(arguments["y1"])
    x2, y2 = float(arguments["x2"]), float(arguments["y2"])
    index = sketch.addGeometry(
        Part.LineSegment(Vector(x1, y1, 0), Vector(x2, y2, 0)), False)
    _pin_point(sketch, index, 1, x1, y1)
    _pin_point(sketch, index, 2, x2, y2)

    document().recompute()
    return "Added a line from (%s, %s) to (%s, %s) in %s. %s" % (
        rounded(x1), rounded(y1), rounded(x2), rounded(y2), sketch.Name,
        _constraint_state(sketch))


def add_arc(arguments):
    """An arc of a circle, measured anticlockwise from the positive X axis."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    cx = float(arguments.get("center_x", 0.0))
    cy = float(arguments.get("center_y", 0.0))
    radius = float(arguments["radius"])
    start = math.radians(float(arguments["start_angle"]))
    end = math.radians(float(arguments["end_angle"]))

    circle = Part.Circle(Vector(cx, cy, 0), Vector(0, 0, 1), radius)
    index = sketch.addGeometry(Part.ArcOfCircle(circle, start, end), False)
    sketch.addConstraint(Sketcher.Constraint("Radius", index, radius))
    _pin_point(sketch, index, 3, cx, cy)

    document().recompute()
    return "Added an arc of radius %s mm centred on (%s, %s) in %s. %s" % (
        rounded(radius), rounded(cx), rounded(cy), sketch.Name,
        _constraint_state(sketch))


def add_polygon(arguments):
    """A regular polygon, sized by the circle its corners sit on."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    sides = int(arguments["sides"])
    if sides < 3:
        return "A polygon needs at least three sides."

    radius = float(arguments["radius"])
    cx = float(arguments.get("center_x", 0.0))
    cy = float(arguments.get("center_y", 0.0))

    points = []
    for corner in range(sides):
        angle = 2.0 * math.pi * corner / sides
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    first = sketch.GeometryCount
    for corner in range(sides):
        x1, y1 = points[corner]
        x2, y2 = points[(corner + 1) % sides]
        sketch.addGeometry(Part.LineSegment(Vector(x1, y1, 0), Vector(x2, y2, 0)), False)

    lines = [first + i for i in range(sides)]
    for corner in range(sides):
        sketch.addConstraint(Sketcher.Constraint(
            "Coincident", lines[corner], 2, lines[(corner + 1) % sides], 1))
    # Every corner pinned: rigid, but unambiguous and fully constrained.
    for corner in range(sides):
        _pin_point(sketch, lines[corner], 1, points[corner][0], points[corner][1])

    document().recompute()
    return "Added a %d-sided polygon of radius %s mm to %s. %s" % (
        sides, rounded(radius), sketch.Name, _constraint_state(sketch))


def add_slot(arguments):
    """A rounded slot: two parallel lines capped with semicircles."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    x1, y1 = float(arguments["x1"]), float(arguments["y1"])
    x2, y2 = float(arguments["x2"]), float(arguments["y2"])
    width = float(arguments["width"])
    radius = width / 2.0

    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return "The two centres are in the same place -- a slot needs a length."

    # Unit vector along the slot, and the perpendicular offset to its sides.
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    px, py = -uy * radius, ux * radius
    angle = math.atan2(uy, ux)

    first = sketch.GeometryCount
    sketch.addGeometry(Part.LineSegment(
        Vector(x1 + px, y1 + py, 0), Vector(x2 + px, y2 + py, 0)), False)
    sketch.addGeometry(Part.LineSegment(
        Vector(x2 - px, y2 - py, 0), Vector(x1 - px, y1 - py, 0)), False)
    sketch.addGeometry(Part.ArcOfCircle(
        Part.Circle(Vector(x2, y2, 0), Vector(0, 0, 1), radius),
        angle + math.pi / 2, angle - math.pi / 2), False)
    sketch.addGeometry(Part.ArcOfCircle(
        Part.Circle(Vector(x1, y1, 0), Vector(0, 0, 1), radius),
        angle - math.pi / 2, angle + math.pi / 2), False)

    top, bottom, cap_end, cap_start = (first, first + 1, first + 2, first + 3)
    sketch.addConstraint(Sketcher.Constraint("Coincident", top, 2, cap_end, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", cap_end, 2, bottom, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", bottom, 2, cap_start, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", cap_start, 2, top, 1))
    sketch.addConstraint(Sketcher.Constraint("Tangent", top, cap_end))
    sketch.addConstraint(Sketcher.Constraint("Tangent", cap_end, bottom))
    sketch.addConstraint(Sketcher.Constraint("Tangent", bottom, cap_start))
    sketch.addConstraint(Sketcher.Constraint("Tangent", cap_start, top))
    sketch.addConstraint(Sketcher.Constraint("Radius", cap_end, radius))
    _pin_point(sketch, cap_start, 3, x1, y1)
    _pin_point(sketch, cap_end, 3, x2, y2)

    document().recompute()
    return "Added a %s mm wide slot from (%s, %s) to (%s, %s) in %s. %s" % (
        rounded(width), rounded(x1), rounded(y1), rounded(x2), rounded(y2),
        sketch.Name, _constraint_state(sketch))


# Constraints between two pieces of geometry, taking no number.
PAIRED = ("Parallel", "Perpendicular", "Equal", "Tangent")
# Constraints on one piece of geometry, taking no number.
SINGLE = ("Horizontal", "Vertical")


def add_constraint(arguments):
    """Add a relationship between drawn elements, by their index."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    kind = str(arguments["type"])
    first = arguments.get("first")
    second = arguments.get("second")
    value = arguments.get("value")

    try:
        if kind in SINGLE:
            constraint = Sketcher.Constraint(kind, int(first))
        elif kind in PAIRED:
            constraint = Sketcher.Constraint(kind, int(first), int(second))
        elif kind == "Coincident":
            constraint = Sketcher.Constraint(
                kind, int(first), int(arguments.get("first_point", 1)),
                int(second), int(arguments.get("second_point", 1)))
        elif kind in ("Radius", "Diameter"):
            constraint = Sketcher.Constraint(kind, int(first), float(value))
        elif kind == "Angle":
            constraint = Sketcher.Constraint(
                kind, int(first), int(second), math.radians(float(value)))
        elif kind in ("Distance", "DistanceX", "DistanceY"):
            constraint = Sketcher.Constraint(
                kind, int(first), int(arguments.get("first_point", 1)),
                int(second), int(arguments.get("second_point", 1)), float(value))
        else:
            return "I do not know the constraint type '%s'." % kind
        sketch.addConstraint(constraint)
    except Exception as exc:
        return "That constraint was rejected: %s: %s" % (type(exc).__name__, exc)

    document().recompute()
    return "Added a %s constraint to %s. %s" % (
        kind, sketch.Name, _constraint_state(sketch))


def mirror_geometry(arguments):
    """Mirror drawn elements about one of the sketch axes."""
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error

    indices = arguments.get("indices")
    if isinstance(indices, (int, float)):
        indices = [indices]
    if not indices:
        return "Say which elements to mirror, by index from describe_sketch."

    axis = str(arguments.get("axis", "X")).upper()
    # In a sketch, geometry -1 is the X axis and -2 is the Y axis.
    reference = {"X": (-1, 0), "Y": (-2, 0), "ORIGIN": (-1, 1)}.get(axis)
    if reference is None:
        return "Mirror about X, Y or origin."

    sketch.addSymmetric([int(i) for i in indices], reference[0], reference[1])
    document().recompute()
    return "Mirrored %d element(s) about %s in %s. %s" % (
        len(indices), axis, sketch.Name, _constraint_state(sketch))


HANDLERS = {
    "create_body": create_body,
    "create_sketch": create_sketch,
    "add_rectangle": add_rectangle,
    "add_circle": add_circle,
    "pad": pad,
    "pocket": pocket,
    "describe_sketch": describe_sketch,
    "delete_geometry": delete_geometry,
    "delete_object": delete_object,
    "add_line": add_line,
    "add_arc": add_arc,
    "add_polygon": add_polygon,
    "add_slot": add_slot,
    "add_constraint": add_constraint,
    "mirror_geometry": mirror_geometry,
}
