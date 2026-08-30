"""Runs the conversation with the model.

The HTTP request happens on a worker thread so FreeCAD stays responsive while
a local model thinks. Tool calls come back to the main thread to be executed,
because FreeCAD documents cannot be touched from a worker.
"""

from PySide import QtCore

from ai_cad import config, ollama, tools

SYSTEM_PROMPT = (
    "You drive FreeCAD for a user who models functional parts for 3D printing. "
    "Use the tools you are given to inspect and change the open document. "
    "Dimensions are in millimetres unless the user says otherwise. "
    "Keep replies short."
)

MAX_TOOL_ROUNDS = 8


class _Request(QtCore.QThread):
    chunk = QtCore.Signal(str)
    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, settings, messages, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._messages = messages

    def run(self):
        try:
            message = ollama.chat(
                self._settings["host"],
                self._settings["model"],
                self._messages,
                tools.SPECS,
                self.chunk.emit,
            )
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
            return
        self.done.emit(message)


class ModelResponder(QtCore.QObject):
    chunk = QtCore.Signal(str)
    finished = QtCore.Signal()
    failed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._request = None
        self._rounds = 0

    def send(self, text):
        self._messages.append({"role": "user", "content": text})
        self._rounds = 0
        self._start()

    def _start(self):
        settings = config.load()
        # Held on self: a QThread that goes out of scope is destroyed mid-run.
        self._request = _Request(settings, list(self._messages), self)
        self._request.chunk.connect(self.chunk)
        self._request.done.connect(self._on_done)
        self._request.failed.connect(self.failed)
        self._request.start()

    def _on_done(self, message):
        self._messages.append(message)
        calls = message.get("tool_calls") or []
        if not calls:
            self.finished.emit()
            return

        self._rounds += 1
        if self._rounds > MAX_TOOL_ROUNDS:
            self.failed.emit("Gave up after %d rounds of tool calls." % MAX_TOOL_ROUNDS)
            return

        for call in calls:
            function = call.get("function") or {}
            name = function.get("name")
            result = tools.dispatch(name, function.get("arguments") or {})
            self._messages.append(
                {"role": "tool", "tool_name": name, "content": result}
            )
        self._start()
