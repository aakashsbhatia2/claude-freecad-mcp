# Conversational FreeCAD

A FreeCAD add-on that adds a chat panel beside the normal modelling tools. The
model calls FreeCAD's own operations, so what it makes is a parametric feature
that can be opened and re-dimensioned by hand.

Providers: Ollama (default) and Claude.

## Running it

```
./setup.sh          # once: fetches the FreeCAD AppImage
./run-freecad.sh    # launches it with the add-on loaded
```

FreeCAD keeps its settings inside `sandbox/`, leaving the normal FreeCAD
profile untouched. The panel appears on the right, and is toggled under
View > Panels.

The **Thinking and tools** strip under the transcript expands to show the
model's reasoning and every tool call and result. Collapsed by default.

## Settings

`sandbox/home/conversational_cad.json`, created by hand. Keys do not go here.

Ollama, the default:

```json
{"provider": "ollama", "host": "http://localhost:11434", "model": "gemma4:26b"}
```

Claude:

```json
{"provider": "anthropic", "model": "claude-opus-5"}
```

## API keys

Keys are read from the environment. Copy `.env.example` to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

`.env` is gitignored. `run-freecad.sh` sources it and exports it into FreeCAD's
environment at launch. A key already exported in the shell is used as-is and
the file is not needed.

## Tools

The complete set. Anything not listed is not available to the model.

### Looking at the document

| Tool | What it does |
|---|---|
| `list_objects` | Bodies, sketches and features in the open document |
| `describe_selection` | What is selected: which face or edge, its size and position |
| `describe_object` | One object's bounding box, position and driving values |
| `list_sketch_geometry` | What is drawn in a sketch, numbered |
| `list_constraints` | The dimensions driving a sketch, numbered |
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
| `undo` | Takes back the last change |
| `save_document` | Saves, with a path the first time |
| `fit_view` | Zooms to fit |
| `set_view` | Points the camera from a named direction |
| `export_stl` | Writes an STL for slicing |
| `export_step` | Writes a STEP for other CAD |

Every call is wrapped in its own undo step, so Ctrl+Z takes back one operation.

## Selection

Fillets, chamfers, holes, sketching on a face and measuring act on the current
selection in the 3D view. Edges are not resolved from descriptions.
