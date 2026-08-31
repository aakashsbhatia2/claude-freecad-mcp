"""Runs the conversation with the model.

The HTTP request happens on a worker thread so FreeCAD stays responsive while
a model thinks. Tool calls come back to the main thread to be executed,
because FreeCAD documents cannot be touched from a worker.

History is kept in one neutral shape and translated by whichever provider is
in use -- see ai_cad/providers.
"""

from PySide import QtCore

from ai_cad import config, providers, tools

SYSTEM_PROMPT = (
    "You drive FreeCAD for a user who models functional parts for 3D printing. "
    "Use the tools you are given to inspect and change the open document. "
    "Dimensions are in millimetres unless the user says otherwise. "
    "Before drawing in a sketch, list what is already in it -- if the user "
    "asks to change a size, change the constraint that drives it rather than "
    "adding a second shape on top. "
    "Refer to objects by the exact names the tools give back; never invent a "
    "name. If a name is not found, call list_objects and use what it reports. "
    "Only the tools you have been given exist -- do not reason about tools "
    "that are not in the list, and do not assume a missing one. "
    "Keep replies short."
)

MAX_TOOL_ROUNDS = 8


class _Request(QtCore.QThread):
    chunk = QtCore.Signal(str)
    thinking = QtCore.Signal(str)
    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, settings, turns, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._turns = turns

    def run(self):
        try:
            turn = providers.chat(
                self._settings,
                SYSTEM_PROMPT,
                self._turns,
                tools.SPECS,
                self.chunk.emit,
                self.thinking.emit,
            )
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
            return
        self.done.emit(turn)


class ModelResponder(QtCore.QObject):
    chunk = QtCore.Signal(str)
    thinking = QtCore.Signal(str)
    note = QtCore.Signal(str)
    finished = QtCore.Signal()
    failed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._turns = []
        self._request = None
        self._rounds = 0

    def send(self, text):
        self._turns.append({"role": "user", "text": text})
        self._rounds = 0
        self._start()

    def _start(self):
        settings = config.load()
        # Held on self: a QThread that goes out of scope is destroyed mid-run.
        self._request = _Request(settings, list(self._turns), self)
        self._request.chunk.connect(self.chunk)
        self._request.thinking.connect(self.thinking)
        self._request.done.connect(self._on_done)
        self._request.failed.connect(self.failed)
        self._request.start()

    def _on_done(self, turn):
        self._turns.append(turn)
        calls = turn.get("tool_calls") or []
        if not calls:
            self.finished.emit()
            return

        self._rounds += 1
        if self._rounds > MAX_TOOL_ROUNDS:
            self.failed.emit("Gave up after %d rounds of tool calls." % MAX_TOOL_ROUNDS)
            return

        for call in calls:
            name = call["name"]
            arguments = call["arguments"]
            self.note.emit("%s(%s)" % (name, _readable(arguments)))
            result = tools.dispatch(name, arguments)
            self.note.emit("  %s" % result.replace("\n", "\n  "))
            self._turns.append({
                "role": "tool",
                "id": call.get("id", ""),
                "name": name,
                "content": result,
            })
        self._start()


def _readable(arguments):
    return ", ".join("%s=%s" % (key, value) for key, value in arguments.items())
