"""Settings, read from a JSON file next to FreeCAD's other user data.

Never put an API key here. Keys come from the environment, loaded out of a
gitignored .env by run-freecad.sh.

Hand-edited for now; step 11 puts a settings dialog on top of it.
"""

import json
import os

import FreeCAD

DEFAULTS = {
    "provider": "ollama",
    "host": "http://localhost:11434",
    "model": "gemma4:26b",
    "context_tokens": 32768,
}

# Each provider's own default model, used when you switch provider without
# naming one.
MODELS = {
    "ollama": "gemma4:26b",
    "anthropic": "claude-opus-5",
}


def path():
    return os.path.join(FreeCAD.getUserAppDataDir(), "conversational_cad.json")


def load():
    try:
        with open(path()) as handle:
            stored = json.load(handle)
    except FileNotFoundError:
        stored = {}

    settings = dict(DEFAULTS, **stored)
    if "model" not in stored:
        settings["model"] = MODELS.get(settings["provider"], DEFAULTS["model"])
    return settings
