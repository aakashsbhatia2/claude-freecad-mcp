"""Talking to a local Ollama server over its HTTP API.

Uses urllib rather than the ollama or requests packages: FreeCAD ships its own
Python 3.11 inside a read-only AppImage, so there is nowhere to install them.
"""

import json
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 600


def chat(host, model, messages, tools, on_chunk):
    """Send the conversation, streaming the reply back through on_chunk.

    Returns the finished assistant message, including any tool calls it wants
    run. Ollama answers with one JSON object per line as it generates.
    """
    body = json.dumps({
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": True,
    }).encode("utf-8")
    request = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    parts = []
    tool_calls = []
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        for line in response:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if payload.get("error"):
                raise RuntimeError(payload["error"])
            message = payload.get("message") or {}
            text = message.get("content") or ""
            if text:
                parts.append(text)
                on_chunk(text)
            tool_calls.extend(message.get("tool_calls") or [])

    return {"role": "assistant", "content": "".join(parts), "tool_calls": tool_calls}
