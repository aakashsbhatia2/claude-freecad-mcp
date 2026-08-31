"""Talking to the Claude API.

Raw HTTP rather than the anthropic package, for the same reason as Ollama:
FreeCAD carries its own Python inside a read-only AppImage, with no pip.

The key is read from the environment, never from a settings file -- see .env
and run-freecad.sh.
"""

import json
import os
import urllib.error
import urllib.request

URL = "https://api.anthropic.com/v1/messages"
VERSION = "2023-06-01"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
TIMEOUT_SECONDS = 600
DEFAULT_MAX_TOKENS = 16000


def _tools(specs):
    """Our tool definitions are in the OpenAI shape; Claude wants its own."""
    out = []
    for spec in specs:
        function = spec["function"]
        out.append({
            "name": function["name"],
            "description": function.get("description", ""),
            "input_schema": function.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


def _messages(turns):
    """Our neutral history, in the shape Claude wants.

    Assistant turns are replayed exactly as they arrived -- Claude requires its
    thinking blocks back unchanged when a conversation continues through tool
    calls. Tool results must all sit in one user message, so runs of them are
    merged.
    """
    out = []
    pending_results = []

    def flush():
        if pending_results:
            out.append({"role": "user", "content": list(pending_results)})
            pending_results.clear()

    for turn in turns:
        if turn["role"] == "tool":
            pending_results.append({
                "type": "tool_result",
                "tool_use_id": turn["id"],
                "content": turn["content"],
            })
            continue

        flush()
        if turn["role"] == "user":
            out.append({"role": "user", "content": turn["text"]})
        elif turn["role"] == "assistant":
            out.append({"role": "assistant", "content": turn["raw"]})

    flush()
    return out


def chat(settings, system, turns, tools, on_chunk, on_thinking=None):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Put it in .env next to run-freecad.sh.")

    body = {
        "model": settings.get("model", "claude-opus-5"),
        "max_tokens": int(settings.get("max_tokens", DEFAULT_MAX_TOKENS)),
        "system": system,
        "messages": _messages(turns),
        "tools": _tools(tools),
        "thinking": {"type": "adaptive", "display": "summarized"},
        "stream": True,
    }

    try:
        return _stream(key, dict(body, fallbacks="default"), with_fallbacks=True,
                       on_chunk=on_chunk, on_thinking=on_thinking)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        if error.code == 400 and ("fallback" in detail or "beta" in detail):
            # The account is not in the server-side fallback beta. Plain request.
            return _stream(key, body, with_fallbacks=False,
                           on_chunk=on_chunk, on_thinking=on_thinking)
        raise RuntimeError(detail.strip() or str(error))


def _stream(key, body, with_fallbacks, on_chunk, on_thinking):
    headers = {
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": VERSION,
    }
    if with_fallbacks:
        headers["anthropic-beta"] = FALLBACK_BETA

    request = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"), headers=headers)

    blocks = []
    partial_json = {}

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        for line in response:
            line = line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            event = json.loads(line[5:].strip())
            kind = event.get("type")

            if kind == "error":
                raise RuntimeError(str(event.get("error")))

            if kind == "content_block_start":
                blocks.append(dict(event["content_block"]))
                partial_json[event["index"]] = ""

            elif kind == "content_block_delta":
                delta = event["delta"]
                index = event["index"]
                if delta["type"] == "text_delta":
                    blocks[index]["text"] = blocks[index].get("text", "") + delta["text"]
                    on_chunk(delta["text"])
                elif delta["type"] == "thinking_delta":
                    blocks[index]["thinking"] = blocks[index].get("thinking", "") + delta["thinking"]
                    if on_thinking is not None:
                        on_thinking(delta["thinking"])
                elif delta["type"] == "signature_delta":
                    blocks[index]["signature"] = delta["signature"]
                elif delta["type"] == "input_json_delta":
                    partial_json[index] += delta["partial_json"]

            elif kind == "content_block_stop":
                index = event["index"]
                if blocks[index].get("type") == "tool_use":
                    raw = partial_json.get(index) or "{}"
                    blocks[index]["input"] = json.loads(raw)

            elif kind == "message_delta":
                if event.get("delta", {}).get("stop_reason") == "refusal":
                    reason = event["delta"].get("stop_details") or {}
                    raise RuntimeError(
                        "Claude declined this request (%s)." % reason.get("category", "no reason given"))

    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    tool_calls = [
        {"id": b["id"], "name": b["name"], "arguments": b.get("input") or {}}
        for b in blocks if b.get("type") == "tool_use"
    ]
    return {"role": "assistant", "text": text, "tool_calls": tool_calls, "raw": blocks}
