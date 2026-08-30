"""Settings, read from a JSON file next to FreeCAD's other user data.

Hand-edited for now; step 11 puts a settings dialog on top of it.
"""

import json
import os

import FreeCAD

DEFAULTS = {
    "host": "http://localhost:11434",
    "model": "gemma4:26b",
}


def path():
    return os.path.join(FreeCAD.getUserAppDataDir(), "conversational_cad.json")


def load():
    try:
        with open(path()) as handle:
            return dict(DEFAULTS, **json.load(handle))
    except FileNotFoundError:
        return dict(DEFAULTS)
