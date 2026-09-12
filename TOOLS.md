# Tools

The complete set. Anything not listed here, it cannot do.

### Looking at the document

| Tool | What it does |
|---|---|
| `list_objects` | Bodies, sketches and features in the open document |
| `describe_selection` | What is selected: which face or edge, its size and position |
| `describe_object` | One object's bounding box, position and driving values |
| `describe_sketch` | Everything in a sketch: what is drawn, the constraints holding it, and what is still free |
| `measure` | Shortest distance between the two things you have clicked |

### Drawing

| Tool | What it does |
|---|---|
| `create_sketch` | New sketch on XY, XZ, YZ, or the face you have clicked |
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
| `pocket` | Cuts a sketch into the solid, to a depth or right through |
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
| `move_object` | Sets or shifts an object's position |
| `rotate_object` | Rotates about X, Y or Z |
| `set_sketch_plane` | Re-attaches a sketch to a different plane or face |
| `delete_object` | Deletes a whole sketch, pad or pocket |

### The document

| Tool | What it does |
|---|---|
| `new_document` | Starts a new, empty document |
| `undo` | Takes back the last change |
| `save_document` | Saves, with a path the first time |
| `fit_view` | Zooms to fit |
| `set_view` | Points the camera from a named direction |
| `export_mesh` | Writes an STL, 3MF or OBJ for slicing |
| `export_step` | Writes a STEP for other CAD |

Every call is one undo step, so Ctrl+Z in FreeCAD takes back one thing at a
time.

## Selection

Fillets, chamfers, holes, sketching on a face and measuring all act on what is
selected in the 3D view. Edges are not worked out from descriptions — click
first, then ask.
