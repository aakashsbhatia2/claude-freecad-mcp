# Tools

The complete set. Anything not listed here, it cannot do.

### Looking at the document

| Tool | What it does |
|---|---|
| `list_objects` | Bodies, sketches and features in the open document |
| `describe_selection` | What is selected: which face or edge, its size and position |
| `describe_object` | One object's bounding box, position and driving values, and whether it is the finished shape |
| `describe_sketch` | Everything in a sketch: what is drawn, the constraints holding it, and what is still free |
| `measure` | Shortest distance between the two things you have clicked |
| `check_interference` | Whether two parts overlap, touch with no gap, or clear each other, and by how much |

### Drawing

| Tool | What it does |
|---|---|
| `create_body` | A new, separate part that is not fused into the others |
| `create_sketch` | New sketch on XY, XZ, YZ, or the face you have clicked, optionally set back from it by a distance |
| `add_rectangle` | Fully constrained rectangle, by width and height |
| `add_circle` | Fully constrained circle, by diameter |
| `add_line` | A single line between two points |
| `add_arc` | Arc of a circle, by radius and start and end angle |
| `add_polygon` | Regular polygon, sized to the corners |
| `add_slot` | Rounded slot between two centres |
| `add_constraint` | Horizontal, vertical, parallel, perpendicular, equal, tangent, coincident, or a dimension |
| `mirror_geometry` | Mirror drawn elements about a sketch axis |
| `delete_geometry` | Remove drawn elements by index |

### Making solids

| Tool | What it does |
|---|---|
| `pad` | Extrudes a sketch into a solid |
| `pocket` | Cuts a sketch into the solid, to a depth or right through, either way; says how much it removed |
| `hole` | Drills into the clicked face; clearance or tapped, counterbored or countersunk |
| `fillet_edges` | Rounds the edges you have clicked |
| `chamfer_edges` | Chamfers the edges you have clicked |
| `linear_pattern` | Repeats a feature in a line |
| `polar_pattern` | Repeats a feature around an axis |
| `mirror_feature` | Mirrored copy of a feature across an origin plane |

### Changing what exists

| Tool | What it does |
|---|---|
| `set_dimension` | Changes a constraint's value |
| `set_property` | Changes a feature's own value, such as a pad's length |
| `rename_object` | Gives an object a meaningful name in the tree |
| `move_object` | Sets or shifts a sketch's or a whole body's position |
| `rotate_object` | Rotates about X, Y or Z |
| `set_sketch_plane` | Re-attaches a sketch to a different plane or face, with the same optional offset |
| `delete_object` | Deletes a sketch, pad or pocket, along with the sketch it was made from, without breaking the rest |

### Reviewing the numbers

| Tool | What it does |
|---|---|
| `mark_dimensions` | Writes the model's driving numbers into the 3D view as dimension lines and labels |
| `clear_dimensions` | Takes them away again |

### The document

| Tool | What it does |
|---|---|
| `new_document` | Starts a new, empty document |
| `switch_document` | Makes another open document the one the tools work on |
| `undo` | Takes back the last change |
| `save_document` | Saves, with a path the first time |
| `fit_view` | Zooms to fit |
| `set_view` | Points the camera from a named direction |
| `export_mesh` | Writes an STL, 3MF or OBJ for slicing, from a named document if you give one |
| `export_step` | Writes a STEP for other CAD |

Every reply starts with the document it acted on, in square brackets. The
tools follow whichever document is active, and clicking a tab in FreeCAD
changes that. Exports also take a `document` and say the size and volume of
what they wrote, and they refuse a feature from partway through the tree.

Every call is one undo step, so Ctrl+Z in FreeCAD takes back one thing at a
time.

## Separate parts

Each physical part goes in its own body: a bracket, a nut, a board. A body is
not fused into the others, moves and rotates as a whole with `move_object` and
`rotate_object`, and can be tested against another with `check_interference`.
Pads and pockets go into the body their sketch is in. With several bodies and
none active, `create_sketch` asks which one rather than guessing.

`check_interference` gives one of three answers: overlapping (with the shared
volume and where it is), touching with no gap — a drawn fit that will not go
together once printed — or clear, with the smallest gap and where it is. Both
parts have to be in the same document.

## Where a sketch can go

A sketch attaches to one of the three origin planes or to a face you have
clicked, and `offset` sets it back from there along the plane's normal. A wall
141 mm out is a sketch on YZ with an offset of 141 — one sketch and one pad,
rather than building it at the origin and trying to move it afterwards. Every
sketch reply says where its (0, 0) is in the model and which way its X and Y
run. That matters most on a clicked face, whose directions are the face's own.

Prefer an offset to a clicked face. A sketch on a face is tied to that face's
number, and FreeCAD renumbers faces when anything earlier in the tree changes,
so the sketch can end up on a different face.

## Cutting

A pocket cuts against the way its sketch faces — down from a sketch on XY —
and `reversed` cuts the other way. It reports the direction and the volume it
removed, and a pocket that removed nothing is taken back out.

Features cannot be moved after the fact: a pad takes its position from the
sketch it was made from, so `move_object` refuses rather than reporting a move
that FreeCAD will undo on the next recompute.

## The finished shape

Only the body's tip describes the finished part. A feature in the middle of the
tree has a shape and a volume of its own, and they read exactly like a finished
part's — `describe_object` says which one you are looking at.

## Selection

Fillets, chamfers, holes, sketching on a face and measuring all act on what is
selected in the 3D view. Edges are not worked out from descriptions — click
first, then ask.
