#!/usr/bin/env python3
"""MCP server: what Claude Code launches to reach FreeCAD.

Claude Code speaks JSON-RPC to this on stdin and stdout. This forwards each
call to the bridge inside the running FreeCAD (addon/ai_cad/server.py) over a
unix socket, and hands the answer back.

Two rules keep it well behaved:

  * stdout carries JSON-RPC and nothing else, one message per line.
  * it never exits because FreeCAD is closed. A server that dies is marked
    failed for the rest of the session and is not retried, so a missing
    FreeCAD has to be an answer, not a crash.

The tool descriptions come from specs.py, which imports nothing -- Claude Code
asks for them once, at startup, usually before FreeCAD is open.
"""

import json
import os
import socket
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

from ai_cad import socket_path               # noqa: E402  (needs the path above)
from ai_cad.specs import SPECS               # noqa: E402

CONNECT_TIMEOUT = 2
CALL_TIMEOUT = 150          # longer than the bridge's own, so it answers first

NO_FREECAD = ("FreeCAD isn't running, so there is nothing to work on. Ask the "
              "user to open FreeCAD, then try again.")

INSTRUCTIONS = (
    "These tools drive a running FreeCAD for a user who models functional "
    "parts for 3D printing. "
    "Dimensions are in millimetres unless the user says otherwise. "
    "Before drawing in a sketch, list what is already in it -- if the user "
    "asks to change a size, change the constraint that drives it rather than "
    "adding a second shape on top. "
    "Refer to objects by the exact names the tools give back; never invent a "
    "name. If a name is not found, call list_objects and use what it reports. "
    "When the user says 'this' or 'that' they mean whatever they have clicked "
    "in FreeCAD: call describe_selection to find out what that is."
)

TOOLS = [{"name": spec["function"]["name"],
          "description": spec["function"]["description"],
          "inputSchema": spec["function"]["parameters"]} for spec in SPECS]


# The connection is held open for the life of this process, so FreeCAD can
# tell in its status bar whether anything is attached.
LINK = None


def _open():
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(CONNECT_TIMEOUT)
    conn.connect(socket_path())
    conn.settimeout(CALL_TIMEOUT)
    return conn, conn.makefile("rwb")


def _drop():
    global LINK
    if LINK is not None:
        try:
            LINK[0].close()
        except OSError:
            pass
        LINK = None


def ask_freecad(request):
    """One round trip to the bridge. Never raises."""
    global LINK
    for attempt in (0, 1):
        if LINK is None:
            try:
                LINK = _open()
            except OSError:
                return False, NO_FREECAD
        stream = LINK[1]
        try:
            stream.write(json.dumps(request).encode("utf-8") + b"\n")
            stream.flush()
            line = stream.readline()
            if not line:
                raise OSError("FreeCAD closed the connection")
            reply = json.loads(line.decode("utf-8"))
            return reply.get("ok", False), reply.get("text", "")
        except socket.timeout:
            _drop()
            return False, "FreeCAD did not answer in time; it may be busy."
        except (OSError, ValueError):
            # FreeCAD was restarted under us: throw the link away and,
            # on the first attempt only, open a fresh one.
            _drop()
    return False, NO_FREECAD


def call_tool(name, arguments):
    ok, text = ask_freecad({"op": "call", "name": name,
                            "arguments": arguments or {}})
    return {"content": [{"type": "text", "text": text}], "isError": not ok}


def handle(method, params):
    """Return a result, or raise KeyError for a method we don't have."""
    if method == "initialize":
        return {
            # Echo the client's version back rather than pinning one: nothing
            # here behaves differently between revisions.
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "freecad", "version": "0.1.0"},
            "instructions": INSTRUCTIONS,
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return call_tool(params.get("name"), params.get("arguments"))
    raise KeyError(method)


def main():
    out = sys.stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue        # nothing to reply to without an id

        # Notifications carry no id and must never be answered -- a reply to
        # notifications/initialized is not valid JSON-RPC.
        if "id" not in message:
            continue

        reply = {"jsonrpc": "2.0", "id": message["id"]}
        try:
            reply["result"] = handle(message.get("method"),
                                     message.get("params") or {})
        except KeyError:
            reply["error"] = {"code": -32601,
                              "message": "Method not found: %s" % message.get("method")}
        except Exception as exc:
            reply["error"] = {"code": -32603,
                              "message": "%s: %s" % (type(exc).__name__, exc)}
        out.write(json.dumps(reply) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
