# Conversational FreeCAD

A FreeCAD add-on that adds a chat panel beside the normal modelling tools. You
keep working the way you always do; the panel is a second way in. The model
drives FreeCAD through the same operations you would click, so everything it
makes is an ordinary parametric feature you can open and re-dimension by hand.

Runs against a local Ollama model by default.

## Running it

```
./setup.sh          # once: fetches the FreeCAD AppImage
./run-freecad.sh    # launches it with the add-on loaded
```

FreeCAD keeps its settings inside `sandbox/`, so your normal FreeCAD profile is
untouched. The panel appears on the right; toggle it under View > Panels.

## Settings

`sandbox/home/conversational_cad.json`, created by hand:

```json
{"host": "http://localhost:11434", "model": "gemma4:26b"}
```

## Tools

What the model is allowed to do. Anything not listed here, it cannot do.

### Looking at the document

| Tool | What it does |
|---|---|
| `list_objects` | Lists the bodies, sketches and features in the open document |
| `describe_selection` | Reports what you have clicked -- which face or edge, its size and position |
| `describe_object` | One object's bounding box, position, and driving values such as a pad's length |

### Changing the document

| Tool | What it does |
|---|---|
| `create_sketch` | New sketch on the XY, XZ or YZ plane, or on the flat face you have clicked |
| `add_rectangle` | Fully constrained rectangle, by width and height in mm |
| `add_circle` | Fully constrained circle, by diameter in mm |
| `pad` | Extrudes a sketch into a solid |
| `pocket` | Cuts a sketch into the solid, to a depth or all the way through |

### Not there yet

No editing, no deleting, no fillets or chamfers, no holes as such, no STL
export. Because nothing can edit, asking to resize something already drawn will
make the model draw it again rather than change it.
