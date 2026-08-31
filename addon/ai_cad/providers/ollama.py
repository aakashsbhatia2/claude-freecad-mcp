"""Talking to a local Ollama server over its HTTP API.

Uses urllib rather than the ollama or requests packages: FreeCAD ships its own
Python 3.11 inside a read-only AppImage, so there is nowhere to install them.
"""

import json
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 600


def _messages(system, turns):
    """Our neutral history, in the shape Ollama wants."""
    out = [{"role": "system", "content": system}]
    for turn in turns:
        if turn["role"] == "user":
            out.append({"role": "user", "content": turn["text"]})
        elif turn["role"] == "assistant":
            message = {"role": "assistant", "content": turn.get("text", "")}
            if turn.get("tool_calls"):
                message["tool_calls"] = [
                    {"function": {"name": call["name"], "arguments": call["arguments"]}}
                    for call in turn["tool_calls"]
                ]
            out.append(message)
        elif turn["role"] == "tool":
            out.append({"role": "tool", "tool_name": turn["name"],
                        "content": turn["content"]})
    return out


def chat(settings, system, turns, tools, on_chunk, on_thinking=None):
    """Send the conversation, streaming the reply back through on_chunk.

    Reasoning models return their working separately from the answer; that
    arrives through on_thinking. Ollama answers with one JSON object per line
    as it generates.
    """
    host = settings.get("host", "http://localhost:11434")
    model = settings["model"]
    context = int(settings.get("context_tokens", 32768))
    messages = _messages(system, turns)
    try:
        return _stream(host, model, messages, tools, on_chunk, on_thinking, True, context)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        if "think" in detail:
            # The model has no separate reasoning step. Ask again without it.
            return _stream(host, model, messages, tools, on_chunk, on_thinking, False, context)
        raise RuntimeError(detail.strip() or str(error))


def _stream(host, model, messages, tools, on_chunk, on_thinking, think, context):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "stream": True,
        # Ollama defaults to a 4096-token context regardless of what the model
        # can take. The tool definitions alone are larger than that, and the
        # overflow is dropped silently from the front -- the model then cannot
        # see the tools that create geometry and insists they do not exist.
        "options": {"num_ctx": context},
    }
    if think:
        payload["think"] = True

    request = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    parts = []
    tool_calls = []
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        for line in response:
            line = line.strip()
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise RuntimeError(chunk["error"])
            message = chunk.get("message") or {}

            reasoning = message.get("thinking") or ""
            if reasoning and on_thinking is not None:
                on_thinking(reasoning)

            text = message.get("content") or ""
            if text:
                parts.append(text)
                on_chunk(text)

            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                tool_calls.append({
                    "id": call.get("id") or "",
                    "name": function.get("name"),
                    "arguments": function.get("arguments") or {},
                })

    return {"role": "assistant", "text": "".join(parts), "tool_calls": tool_calls}
