"""The bridge: a socket inside FreeCAD that runs tool calls on the GUI thread.

FreeCAD may only touch a document from the thread that draws the window, so
nothing here calls a tool where it arrives. The accept loop drops each request
into a queue and waits; a timer on the GUI thread picks it up, runs it, and
sets the event the waiting thread is sitting on.

One line of JSON in, one line of JSON out:

    {"op": "list_tools"}                          {"ok": true, "tools": [...]}
    {"op": "call", "name": ..., "arguments": {}}  {"ok": bool, "text": "..."}
    {"op": "reload_tools"}                        {"ok": bool, "text": "..."}
"""

import atexit
import json
import os
import queue
import socket
import threading

from PySide import QtCore, QtWidgets

from ai_cad import socket_path

DRAIN_MS = 50           # how often the GUI thread looks at the queue
CALL_TIMEOUT = 120      # seconds a client waits for one call

BRIDGE = None


def destroy(timer):
    """Stop a repeating timer and delete it straight away.

    One left alive when Python shuts down takes FreeCAD's exit with it: Qt
    tries to disconnect it after the interpreter has already gone. Stopping
    is not enough, the object itself has to go.
    """
    timer.stop()
    for name in ("shiboken6", "shiboken2"):
        try:
            module = __import__(name)
        except ImportError:
            continue
        module.delete(timer)
        return


class Bridge(QtCore.QObject):

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.last_tool = None
        self.clients = 0
        self._pending = queue.Queue()
        self._busy = False
        self._socket = None
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._drain)
        self._timer.start(DRAIN_MS)

    # -- GUI thread ---------------------------------------------------------

    def _drain(self):
        if self._busy or self._pending.empty():
            return
        # A modal dialog runs an event loop of its own, and this timer keeps
        # firing inside it. Starting a tool there would nest one undo
        # transaction in another, so leave the queue alone until it closes.
        if QtWidgets.QApplication.activeModalWidget() is not None:
            return

        request, reply = self._pending.get()
        self._busy = True
        try:
            reply["value"] = self._run(request)
        except Exception as exc:
            reply["value"] = {"ok": False,
                              "text": "%s: %s" % (type(exc).__name__, exc)}
        finally:
            self._busy = False
            reply["done"].set()

    def _run(self, request):
        from ai_cad import tools

        op = request.get("op")
        if op == "list_tools":
            return {"ok": True, "tools": tools.SPECS}
        if op == "reload_tools":
            return {"ok": True, "text": tools.reload()}
        if op == "call":
            name = request.get("name")
            ok, text = tools.call(name, request.get("arguments") or {})
            self.last_tool = name
            return {"ok": ok, "text": text}
        return {"ok": False, "text": "Unknown request %r." % op}

    # -- accept thread ------------------------------------------------------

    def _serve(self):
        while True:
            try:
                conn, _ = self._socket.accept()
            except OSError:
                return          # the socket was closed; FreeCAD is going away
            self.clients += 1
            try:
                self._converse(conn)
            except OSError:
                pass            # client hung up mid-request
            finally:
                self.clients -= 1
                conn.close()

    def _converse(self, conn):
        stream = conn.makefile("rwb")
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line.decode("utf-8"))
            except ValueError as exc:
                reply = {"ok": False, "text": "Bad request: %s" % exc}
            else:
                reply = self._submit(request)
            stream.write(json.dumps(reply).encode("utf-8") + b"\n")
            stream.flush()

    def _submit(self, request):
        """Hand the request to the GUI thread and wait for it to come back."""
        reply = {"done": threading.Event(), "value": None}
        self._pending.put((request, reply))
        if not reply["done"].wait(CALL_TIMEOUT):
            return {"ok": False, "text": (
                "FreeCAD did not answer within %d seconds. It may have a "
                "dialog open." % CALL_TIMEOUT)}
        return reply["value"]

    def shutdown(self):
        """Called as FreeCAD exits."""
        destroy(self._timer)
        if self._socket is not None:
            self._socket.close()          # unblocks the accept thread
            self._socket = None
        path = socket_path()
        if os.path.exists(path):
            os.unlink(path)

    def listen(self, path):
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(path)
        self._socket.listen(4)
        threading.Thread(target=self._serve, daemon=True).start()


def _in_use(path):
    """True if something is already listening -- as opposed to a stale file."""
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.5)
    try:
        probe.connect(path)
        return True
    except OSError:
        return False
    finally:
        probe.close()


def start(parent=None):
    """Open the socket. Called once, from the GUI thread, at startup."""
    global BRIDGE
    if BRIDGE is not None:
        return BRIDGE

    path = socket_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        if _in_use(path):
            raise OSError("another FreeCAD is already listening on %s" % path)
        os.unlink(path)         # left behind by a crash

    BRIDGE = Bridge(parent)
    BRIDGE.listen(path)
    atexit.register(BRIDGE.shutdown)
    return BRIDGE
