"""Every tool description, in one place and away from FreeCAD.

The MCP server has to answer 'what can you do?' before FreeCAD is
necessarily running, so this file imports nothing. The code that does
the work stays in the module named above each group.
"""


def _spec(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
            },
        },
    }


SPECS = [

    # inspect
    _spec("list_objects",
          "List everything in the open FreeCAD document: bodies, sketches "
          "and features, with their types. Use this first to see what "
          "exists."),
    _spec("describe_selection",
          "Describe what the user has currently clicked in the 3D view or "
          "the tree -- which faces, edges or objects, and their size and "
          "position. Use this whenever the user says 'this' or 'that'."),
    _spec("describe_object",
          "Report one object's dimensions, position and driving values, "
          "such as a pad's length or a box's sides.",
          {
              "name": {"type": "string", "description": "The object's label in the tree, or its internal name."},
          },
          ["name"]),

    # build
    _spec("create_sketch",
          "Start a new empty sketch, either on one of the three origin "
          "planes or on the flat face the user has clicked. Creates a body "
          "if the document has none. Use the name it gives back for every "
          "later call -- do not invent one.",
          {
              "plane": {"type": "string", "enum": ["XY", "XZ", "YZ", "selection"], "description": "Which plane to draw on. Use 'selection' for the clicked face."},
              "name": {"type": "string", "description": "What to call it in the tree. Optional."},
          }),
    _spec("add_rectangle",
          "Draw a fully constrained rectangle in a sketch. Sizes are in "
          "millimetres. The centre defaults to the sketch origin.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "width": {"type": "number", "description": "Size along X, in mm."},
              "height": {"type": "number", "description": "Size along Y, in mm."},
              "center_x": {"type": "number", "description": "Centre X, in mm. Default 0."},
              "center_y": {"type": "number", "description": "Centre Y, in mm. Default 0."},
          },
          ["sketch", "width", "height"]),
    _spec("add_circle",
          "Draw a fully constrained circle in a sketch, sized by diameter "
          "in mm.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "diameter": {"type": "number", "description": "Diameter in mm."},
              "center_x": {"type": "number", "description": "Centre X, in mm. Default 0."},
              "center_y": {"type": "number", "description": "Centre Y, in mm. Default 0."},
          },
          ["sketch", "diameter"]),
    _spec("pad",
          "Extrude a sketch into a solid. Use symmetric to grow equally "
          "both ways from the sketch plane, reversed to go the other way.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch to extrude."},
              "length": {"type": "number", "description": "Depth in mm."},
              "symmetric": {"type": "boolean", "description": "Extrude both ways. Default false."},
              "reversed": {"type": "boolean", "description": "Extrude the opposite way. Default false."},
          },
          ["sketch", "length"]),
    _spec("pocket",
          "Cut a sketch into the existing solid, to a depth or all the way "
          "through.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch to cut with."},
              "depth": {"type": "number", "description": "Depth in mm. Ignored if through_all is true."},
              "through_all": {"type": "boolean", "description": "Cut all the way through. Default false."},
          },
          ["sketch"]),
    _spec("describe_sketch",
          "The whole state of one sketch: what is drawn, numbered, with "
          "positions and sizes, and under each element the constraints "
          "holding it, numbered too. Ends with how many degrees of freedom "
          "are left. Use this before drawing in a sketch, before deleting "
          "anything, and before changing a size -- the constraint numbers "
          "it gives back are the ones set_dimension takes.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
          },
          ["sketch"]),
    _spec("delete_geometry",
          "Delete drawn elements from a sketch by their index from "
          "describe_sketch. A rectangle is four separate lines, so "
          "removing one means passing all four indices.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "indices": {"type": "array", "items": {"type": "integer"}, "description": "Indices to delete, as reported by describe_sketch."},
          },
          ["sketch", "indices"]),
    _spec("delete_object",
          "Delete a whole object -- a sketch, a pad, a pocket -- from the "
          "document. Deleting a sketch that a pad depends on will break the "
          "pad, so check with list_objects first.",
          {
              "name": {"type": "string", "description": "The object's label or internal name."},
          },
          ["name"]),
    _spec("add_line",
          "Draw a single line in a sketch between two points, in mm.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "x1": {"type": "number"},
              "y1": {"type": "number"},
              "x2": {"type": "number"},
              "y2": {"type": "number"},
          },
          ["sketch", "x1", "y1", "x2", "y2"]),
    _spec("add_arc",
          "Draw an arc of a circle. Angles are degrees anticlockwise from "
          "the positive X axis.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "radius": {"type": "number", "description": "Radius in mm."},
              "start_angle": {"type": "number", "description": "Start angle in degrees."},
              "end_angle": {"type": "number", "description": "End angle in degrees."},
              "center_x": {"type": "number", "description": "Centre X in mm. Default 0."},
              "center_y": {"type": "number", "description": "Centre Y in mm. Default 0."},
          },
          ["sketch", "radius", "start_angle", "end_angle"]),
    _spec("add_polygon",
          "Draw a regular polygon -- a hexagon for a nut pocket, say. The "
          "radius is to the corners, not the flats.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "sides": {"type": "integer", "description": "Number of sides, 3 or more."},
              "radius": {"type": "number", "description": "Corner radius in mm."},
              "center_x": {"type": "number", "description": "Centre X in mm. Default 0."},
              "center_y": {"type": "number", "description": "Centre Y in mm. Default 0."},
          },
          ["sketch", "sides", "radius"]),
    _spec("add_slot",
          "Draw a rounded slot between two centres -- the shape you cut for "
          "an adjustable screw. Width is the full width, end to end.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "x1": {"type": "number"},
              "y1": {"type": "number"},
              "x2": {"type": "number"},
              "y2": {"type": "number"},
              "width": {"type": "number", "description": "Slot width in mm."},
          },
          ["sketch", "x1", "y1", "x2", "y2", "width"]),
    _spec("add_constraint",
          "Add a relationship between drawn elements: horizontal, vertical, "
          "parallel, perpendicular, equal, tangent, coincident, or a "
          "dimension. Indices come from describe_sketch. Point numbers "
          "are 1 for the start, 2 for the end, 3 for a centre.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "type": {"type": "string", "enum": ["Horizontal", "Vertical", "Parallel", "Perpendicular", "Equal", "Tangent", "Coincident", "Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"], "description": "Which constraint to apply."},
              "first": {"type": "integer", "description": "First element's index."},
              "second": {"type": "integer", "description": "Second element's index, where two are needed."},
              "first_point": {"type": "integer", "description": "1 start, 2 end, 3 centre. Default 1."},
              "second_point": {"type": "integer", "description": "1 start, 2 end, 3 centre. Default 1."},
              "value": {"type": "number", "description": "The number, for dimensional constraints."},
          },
          ["sketch", "type", "first"]),
    _spec("mirror_geometry",
          "Mirror drawn elements about the sketch's X axis, Y axis or "
          "origin.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "indices": {"type": "array", "items": {"type": "integer"}, "description": "Indices to mirror, from describe_sketch."},
              "axis": {"type": "string", "enum": ["X", "Y", "origin"], "description": "What to mirror about. Default X."},
          },
          ["sketch", "indices"]),

    # edit
    _spec("set_dimension",
          "Change one constraint's value. This is how to resize something "
          "that is already drawn -- never draw a second shape to change a "
          "size.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "index": {"type": "integer", "description": "Constraint index from describe_sketch."},
              "value": {"type": "number", "description": "New value, mm or degrees."},
          },
          ["sketch", "index", "value"]),
    _spec("set_property",
          "Change a feature's own value, such as a pad's Length or a "
          "pocket's Depth. Use describe_object to see what a feature has.",
          {
              "name": {"type": "string", "description": "The object's label or internal name."},
              "property": {"type": "string", "description": "Property name, e.g. Length."},
              "value": {"description": "The new value."},
          },
          ["name", "property", "value"]),
    _spec("rename_object",
          "Give an object a meaningful name in the tree.",
          {
              "name": {"type": "string", "description": "Current label or internal name."},
              "new_name": {"type": "string", "description": "The new label."},
          },
          ["name", "new_name"]),
    _spec("move_object",
          "Move an object. Absolute position by default; set relative to "
          "shift it from where it is.",
          {
              "name": {"type": "string", "description": "The object to move."},
              "x": {"type": "number", "description": "X in mm. Default 0."},
              "y": {"type": "number", "description": "Y in mm. Default 0."},
              "z": {"type": "number", "description": "Z in mm. Default 0."},
              "relative": {"type": "boolean", "description": "Shift rather than set. Default false."},
          },
          ["name"]),
    _spec("rotate_object",
          "Rotate an object about the X, Y or Z axis, in degrees.",
          {
              "name": {"type": "string", "description": "The object to rotate."},
              "axis": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Axis to turn about."},
              "angle": {"type": "number", "description": "Degrees."},
          },
          ["name", "angle"]),
    _spec("set_sketch_plane",
          "Re-attach a sketch to a different origin plane, or to the face "
          "the user has clicked.",
          {
              "sketch": {"type": "string", "description": "Name of the sketch."},
              "plane": {"type": "string", "enum": ["XY", "XZ", "YZ", "selection"], "description": "Where to put it."},
          },
          ["sketch", "plane"]),

    # dress
    _spec("fillet_edges",
          "Round the edges the user has clicked. Check describe_selection "
          "first -- this acts on the current selection, nothing else.",
          {
              "radius": {"type": "number", "description": "Radius in mm."},
          },
          ["radius"]),
    _spec("chamfer_edges",
          "Cut a flat chamfer on the edges the user has clicked.",
          {
              "size": {"type": "number", "description": "Chamfer size in mm."},
          },
          ["size"]),
    _spec("hole",
          "Drill holes into the flat face the user has clicked. Give a "
          "diameter, or a thread size such as M4 for a clearance hole. "
          "Positions are measured on that face from its origin.",
          {
              "diameter": {"type": "number", "description": "Hole diameter in mm."},
              "thread": {"type": "string", "description": "Metric size such as M3, M4. Sets a clearance diameter, or a tapped hole if threaded is true."},
              "threaded": {"type": "boolean", "description": "Tap the hole rather than drill clearance."},
              "through_all": {"type": "boolean", "description": "Go right through. Default true."},
              "depth": {"type": "number", "description": "Depth in mm when not going through."},
              "head": {"type": "string", "enum": ["none", "counterbore", "countersink"], "description": "Head recess. Default none."},
              "positions": {"type": "array", "description": "Where to put them on the face, in mm. Defaults to one at the origin.", "items": {"type": "object", "properties": {"x": {"type": "number"}, "y": {"type": "number"}}}},
          }),

    # pattern
    _spec("linear_pattern",
          "Repeat a feature in a straight line, such as a row of holes. The "
          "length is the distance from the first copy to the last.",
          {
              "feature": {"type": "string", "description": "The feature to repeat, e.g. Hole."},
              "direction": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Which way to go."},
              "length": {"type": "number", "description": "Total span in mm."},
              "count": {"type": "integer", "description": "How many copies in total, including the original."},
              "reversed": {"type": "boolean", "description": "Go the other way. Default false."},
          },
          ["feature", "length", "count"]),
    _spec("polar_pattern",
          "Repeat a feature around an axis, such as bolts on a circle.",
          {
              "feature": {"type": "string", "description": "The feature to repeat."},
              "axis": {"type": "string", "enum": ["X", "Y", "Z"], "description": "Axis to turn about. Default Z."},
              "angle": {"type": "number", "description": "Degrees to spread over. Default 360."},
              "count": {"type": "integer", "description": "How many copies in total."},
          },
          ["feature", "count"]),
    _spec("mirror_feature",
          "Make a mirrored copy of a feature across an origin plane.",
          {
              "feature": {"type": "string", "description": "The feature to mirror."},
              "plane": {"type": "string", "enum": ["XY", "XZ", "YZ"], "description": "Mirror plane. Default YZ."},
          },
          ["feature"]),

    # document
    _spec("new_document",
          "Start a new, empty FreeCAD document. Only needed when nothing is "
          "open -- the sketch tools make one on their own.",
          {
              "name": {"type": "string", "description": "What to call it. Optional."},
          }),
    _spec("undo",
          "Undo the last change. Use this when you have just done something "
          "the user did not want."),
    _spec("save_document",
          "Save the document. A path is only needed the first time.",
          {
              "path": {"type": "string", "description": "Where to save, if it has no file yet."},
          }),
    _spec("fit_view",
          "Zoom the 3D view so everything is visible."),
    _spec("set_view",
          "Point the camera at the model from a named direction.",
          {
              "direction": {"type": "string", "enum": ["isometric", "top", "bottom", "front", "rear", "left", "right"], "description": "Which way to look from."},
          }),
    _spec("measure",
          "Measure the shortest distance between the two things the user "
          "has clicked."),
    _spec("export_stl",
          "Write an STL file for slicing and printing.",
          {
              "path": {"type": "string", "description": "Where to write the file."},
              "name": {"type": "string", "description": "Which body to export. Defaults to the only one."},
          },
          ["path"]),
    _spec("export_step",
          "Write a STEP file, which keeps exact curved surfaces for other "
          "CAD.",
          {
              "path": {"type": "string", "description": "Where to write the file."},
              "name": {"type": "string", "description": "Which body to export. Defaults to the only one."},
          },
          ["path"]),
]
