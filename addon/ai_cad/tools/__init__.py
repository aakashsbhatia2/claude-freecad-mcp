"""Everything the model is allowed to do, gathered in one place.

    inspect   look at the document, the selection, one object
    build     sketches, geometry, pad, pocket, delete
    edit      change what exists: dimensions, properties, placement
    dress     fillets, chamfers, holes
    pattern   repeat and mirror features
    document  undo, save, view, measure, export

All of them run on the GUI thread -- FreeCAD documents are not safe to touch
from a worker.
"""

import FreeCAD

from ai_cad.tools import build, document, dress, edit, inspect, pattern

MODULES = (inspect, build, edit, dress, pattern, document)

SPECS = [spec for module in MODULES for spec in module.SPECS]

HANDLERS = {}
for _module in MODULES:
    HANDLERS.update(_module.HANDLERS)


def dispatch(name, arguments):
    handler = HANDLERS.get(name)
    if handler is None:
        return "There is no tool called %s." % name

    # One transaction per call, so a mistake can be taken back in one step --
    # by the undo tool, or by the user pressing Ctrl+Z.
    doc = FreeCAD.ActiveDocument
    if doc is not None:
        doc.openTransaction(name)
    try:
        return handler(arguments)
    except Exception as exc:
        return "%s failed: %s: %s" % (name, type(exc).__name__, exc)
    finally:
        if doc is not None:
            doc.commitTransaction()
