"""Everything the model is allowed to do, gathered in one place.

Read-only tools live in inspect, the ones that change the document in build.
All of them run on the GUI thread -- FreeCAD documents are not safe to touch
from a worker.
"""

from ai_cad.tools import build, inspect

SPECS = inspect.SPECS + build.SPECS

HANDLERS = dict(inspect.HANDLERS)
HANDLERS.update(build.HANDLERS)


def dispatch(name, arguments):
    handler = HANDLERS.get(name)
    if handler is None:
        return "There is no tool called %s." % name
    try:
        return handler(arguments)
    except Exception as exc:
        return "%s failed: %s: %s" % (name, type(exc).__name__, exc)
