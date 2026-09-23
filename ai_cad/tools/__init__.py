"""Everything the model is allowed to do, gathered in one place.

    inspect   look at the document, the selection, one object
    build     sketches, geometry, pad, pocket, delete
    edit      change what exists: dimensions, properties, placement
    dress     fillets, chamfers, holes
    pattern   repeat and mirror features
    dimensio  write the model's own numbers into the 3D view
    document  undo, save, view, measure, export

All of them run on the GUI thread -- FreeCAD documents are not safe to touch
from a worker.
"""

import importlib

import FreeCAD

from ai_cad import specs, util
from ai_cad.tools import (build, dimensions, document, dress, edit, inspect,
                          pattern)

MODULES = (inspect, build, edit, dress, pattern, dimensions, document)

# What each tool does lives in ai_cad/specs.py, outside this package because
# opening this one imports FreeCAD -- and the MCP server has to read the
# descriptions with FreeCAD closed.
SPECS = specs.SPECS
HANDLERS = {}


def _rebuild():
    HANDLERS.clear()
    for module in MODULES:
        HANDLERS.update(module.HANDLERS)


_rebuild()


def reload():
    """Pick up edits to the tool modules without restarting FreeCAD.

    util goes first: the tool modules import names from it, and a stale copy
    would survive in every one of them otherwise.
    """
    global SPECS
    importlib.reload(util)
    for module in MODULES:
        importlib.reload(module)
    importlib.reload(specs)
    SPECS = specs.SPECS
    _rebuild()
    return "Reloaded %d tools." % len(SPECS)


def call(name, arguments):
    """Run one tool. Returns (worked, what to tell the caller)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return False, "There is no tool called %s." % name

    # One transaction per call, so a mistake can be taken back in one step --
    # by the undo tool, or by the user pressing Ctrl+Z.
    doc = FreeCAD.ActiveDocument
    if doc is not None:
        doc.openTransaction(name)
    try:
        return True, _labelled(handler(arguments))
    except Exception as exc:
        return False, _labelled("%s failed: %s: %s" % (name, type(exc).__name__, exc))
    finally:
        if doc is not None:
            doc.commitTransaction()


def _labelled(text):
    """Start every reply with the document it happened in.

    The tools act on whichever document is active, and the user can change
    that by clicking a tab at any moment. Naming it on every reply is what
    lets a wrong one be noticed before anything is exported from it.
    """
    doc = FreeCAD.ActiveDocument
    return "[%s] %s" % (doc.Label, text) if doc is not None else text


def dispatch(name, arguments):
    return call(name, arguments)[1]
