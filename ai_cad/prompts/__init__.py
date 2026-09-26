"""Text sent to the model, kept apart from the code that sends it.

Each prompt is a Markdown file in this folder. Nothing here may import FreeCAD
or Qt: the MCP server reads these with FreeCAD closed.
"""

import os

HERE = os.path.dirname(os.path.realpath(__file__))


def load(name):
    """The text of <name>.md, or "" if it can't be read.

    A missing file must not stop the MCP server starting: a server that dies
    is marked failed for the rest of the session.
    """
    try:
        with open(os.path.join(HERE, name + ".md"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""
