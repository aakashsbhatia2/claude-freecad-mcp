# PLAN — Conversational CAD add-on for FreeCAD

## Problem

I model functional parts for around the house in Onshape and FreeCAD — brackets, mounts,
adapters, things with real measurements. The manual workflow is fine; what's missing is
being able to say "make a 20 x 40 box", "pad this 5mm", "fillet the edge I've selected at
3mm" instead of clicking through the same dialogs.

The goal is a second way of driving FreeCAD, not a new CAD program. Everything the AI does
must land in the document as ordinary parametric features that I can then open, re-dimension
and take over by hand — and everything I build by hand must be something the AI can read and
modify. Manual mode is FreeCAD itself, untouched.

It runs locally against Ollama, with the option to point at Anthropic or OpenAI instead.

## Considerations

- **Additive only.** Nothing in FreeCAD's own code changes. The add-on is a workbench: it
  registers itself, sits in the workbench dropdown, and its panel and commands don't exist
  until selected. Building FreeCAD from source was considered and dropped — hours of
  compiling OpenCASCADE/Coin3D/Qt, repeated on every upstream update, buying nothing that a
  workbench can't already do.
- **Sandboxed profile.** FreeCAD is launched from a project script pointing at a config
  folder inside the project. The everyday `~/.local/share/FreeCAD` profile never sees the
  add-on. Two profiles, one FreeCAD binary.
- **Tools are FreeCAD operations.** The model doesn't write geometry or free-form Python. It
  calls a fixed set of tools that map onto the operations I'd otherwise click. This is what
  keeps the result parametric and editable.
- **References come from selection.** "Fillet this edge" acts on what's selected in the 3D
  view. Working out which edge is "the top left one" from words alone is a much harder
  problem and is deliberately out of scope for now — it picks wrong often enough to be worse
  than useless.
- **Changes apply immediately.** No confirm step. FreeCAD's undo is the safety net, with one
  undo transaction per chat request so a multi-step change reverts as a unit. A preview /
  approve flow can come later.
- **Local model quality is the main risk.** 12GB of VRAM holds a 14B-class model outright;
  a ~30B model runs with part of it in the 96GB of system RAM, slower but usable, and is
  meaningfully better at tool calling. Either way, expect more misfires than a hosted model —
  the provider is configurable partly so this can be measured rather than guessed.
- **Out of scope for v1:** assemblies, revolve/loft/sweep, patterns, mesh or generative 3D,
  drawings, natural-language edge resolution, multi-body operations.

## Steps

1. **Sandboxed FreeCAD.** Get a FreeCAD AppImage into the project, plus a launch script that
   runs it against a project-local config and add-on folder. Check: it starts, and the
   everyday install is unaffected.
2. **Empty workbench.** Minimal add-on that appears in the workbench dropdown and opens an
   empty dockable panel. Check: present in the sandbox, absent in normal FreeCAD.
3. **Chat panel.** Message list, input box, streaming output, busy state. No model yet —
   echoes back. Check: usable as a UI.
4. **Provider layer.** Config file for provider (ollama / anthropic / openai), model name and
   API key, behind one call interface with tool calling. Check: a trivial tool round-trips on
   all three.
5. **Read-only tools.** List the feature tree, describe the current selection, report an
   object's dimensions and placement. Check: ask questions about a part I made by hand and
   get right answers.
6. **Sketch and solid tools.** New sketch on a plane or flat face; rectangle and circle with
   dimensions; pad; pocket. Check: "make a 40 x 20 x 5 plate" produces a normal editable
   Part Design body.
7. **Dress-up tools.** Hole on a selected face at a position with diameter and depth; fillet
   and chamfer on selected edges. Check: select an edge, ask for a 3mm fillet, get one.
8. **Edit and delete tools.** Change an existing feature's parameters; delete a feature;
   recompute and feed any errors back to the model. Check: "make that pad 8mm" works on a
   feature I created by hand.
9. **Export.** Export a body to STL at a chosen path. Check: file opens in a slicer.
10. **Agent loop hardening.** Multi-step requests, one undo transaction per request, recompute
    failures surfaced in chat, sensible behaviour when the model asks for something invalid.
11. **Settings UI.** Provider, model and key editable from inside FreeCAD rather than a file.
