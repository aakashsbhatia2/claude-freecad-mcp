"""Tools that change the document: sketches, geometry, pads and pockets.

Everything is made the way Part Design makes it by hand -- a Body, a sketch
attached to a plane or a face, fully constrained geometry, then a pad or a
pocket driven by that sketch. The result is a normal parametric feature the
user can open and re-dimension.
"""

import FreeCAD
import FreeCADGui
import Part
import Sketcher

from FreeCAD import Vector

from ai_cad.util import document, find, rounded

PLANES = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}


def _require_document():
    doc = document()
    if doc is None:
        doc = FreeCAD.newDocument("Unnamed")
    return doc


def _active_body(doc):
    """The body new features go into, creating one on first use."""
    view = FreeCADGui.ActiveDocument.ActiveView
    body = view.getActiveObject("pdbody")
    if body is not None and body.Document is doc:
        return body

    bodies = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]
    body = bodies[0] if bodies else doc.addObject("PartDesign::Body", "Body")
    view.setActiveObject("pdbody", body)
    return body


def _origin_plane(body, plane):
    wanted = PLANES[plane]
    for feature in body.Origin.OriginFeatures:
        if feature.Name.startswith(wanted):
            return feature
    return None


def _sketch_named(name):
    sketch = find(name)
    if sketch is None:
        return None, "There is no sketch called '%s'." % name
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


def create_sketch(arguments):
    """Start a sketch on an origin plane, or on the face the user has clicked."""
    plane = (arguments.get("plane") or "XY").upper()
    doc = _require_document()
    body = _active_body(doc)

    if plane == "SELECTION":
        selection = FreeCADGui.Selection.getSelectionEx()
        faces = [(e.Object, n) for e in selection for n in e.SubElementNames
                 if n.startswith("Face")]
        if not faces:
            return "No face is selected. Ask the user to click the face to sketch on."
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
    doc.recompute()
    return "Created %s on %s, in body %s. It is empty." % (
        sketch.Name, where, body.Label)


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
        return "The sketch is fully constrained."
    return "The sketch is not fully constrained yet."


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


def pad(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error
    if sketch.GeometryCount == 0:
        return "%s is empty -- draw something in it first." % sketch.Name

    doc = document()
    body = _active_body(doc)
    feature = body.newObject("PartDesign::Pad", "Pad")
    feature.Profile = sketch
    feature.Length = float(arguments["length"])
    feature.Midplane = bool(arguments.get("symmetric", False))
    feature.Reversed = bool(arguments.get("reversed", False))

    problem = _report(feature, doc)
    if problem:
        return problem
    return "Padded %s by %s mm as %s." % (
        sketch.Name, rounded(feature.Length.Value), feature.Name)


def pocket(arguments):
    sketch, error = _sketch_named(arguments.get("sketch"))
    if error:
        return error
    if sketch.GeometryCount == 0:
        return "%s is empty -- draw something in it first." % sketch.Name

    doc = document()
    body = _active_body(doc)
    feature = body.newObject("PartDesign::Pocket", "Pocket")
    feature.Profile = sketch

    if arguments.get("through_all"):
        feature.Type = 1  # ThroughAll
        depth = "all the way through"
    else:
        feature.Length = float(arguments["depth"])
        depth = "%s mm deep" % rounded(feature.Length.Value)

    problem = _report(feature, doc)
    if problem:
        return problem
    return "Cut %s into the body, %s, as %s." % (sketch.Name, depth, feature.Name)


HANDLERS = {
    "create_sketch": create_sketch,
    "add_rectangle": add_rectangle,
    "add_circle": add_circle,
    "pad": pad,
    "pocket": pocket,
}

SPECS = [
    {
        "type": "function",
        "function": {
            "name": "create_sketch",
            "description": (
                "Start a new empty sketch, either on one of the three origin "
                "planes or on the flat face the user has clicked. Creates a "
                "body if the document has none. Returns the sketch's name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plane": {
                        "type": "string",
                        "enum": ["XY", "XZ", "YZ", "selection"],
                        "description": "Which plane to draw on. Use 'selection' for the clicked face.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_rectangle",
            "description": (
                "Draw a fully constrained rectangle in a sketch. Sizes are in "
                "millimetres. The centre defaults to the sketch origin."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch": {"type": "string", "description": "Name of the sketch."},
                    "width": {"type": "number", "description": "Size along X, in mm."},
                    "height": {"type": "number", "description": "Size along Y, in mm."},
                    "center_x": {"type": "number", "description": "Centre X, in mm. Default 0."},
                    "center_y": {"type": "number", "description": "Centre Y, in mm. Default 0."},
                },
                "required": ["sketch", "width", "height"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_circle",
            "description": "Draw a fully constrained circle in a sketch, sized by diameter in mm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch": {"type": "string", "description": "Name of the sketch."},
                    "diameter": {"type": "number", "description": "Diameter in mm."},
                    "center_x": {"type": "number", "description": "Centre X, in mm. Default 0."},
                    "center_y": {"type": "number", "description": "Centre Y, in mm. Default 0."},
                },
                "required": ["sketch", "diameter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pad",
            "description": (
                "Extrude a sketch into a solid. Use symmetric to grow equally "
                "both ways from the sketch plane, reversed to go the other way."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch": {"type": "string", "description": "Name of the sketch to extrude."},
                    "length": {"type": "number", "description": "Depth in mm."},
                    "symmetric": {"type": "boolean", "description": "Extrude both ways. Default false."},
                    "reversed": {"type": "boolean", "description": "Extrude the opposite way. Default false."},
                },
                "required": ["sketch", "length"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pocket",
            "description": "Cut a sketch into the existing solid, to a depth or all the way through.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sketch": {"type": "string", "description": "Name of the sketch to cut with."},
                    "depth": {"type": "number", "description": "Depth in mm. Ignored if through_all is true."},
                    "through_all": {"type": "boolean", "description": "Cut all the way through. Default false."},
                },
                "required": ["sketch"],
            },
        },
    },
]
