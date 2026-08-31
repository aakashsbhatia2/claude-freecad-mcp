"""Where replies come from. One module per service, one shared shape.

A provider takes the system prompt, the conversation so far, and the tool
definitions, and returns the assistant's turn:

    {"role": "assistant", "text": ..., "tool_calls": [...], "raw": ...}

'raw' is whatever that service needs handed back verbatim next time -- Claude
requires its thinking blocks returned unchanged. Text arrives through on_chunk
as it is generated, reasoning through on_thinking.
"""

from ai_cad.providers import anthropic, ollama

PROVIDERS = {
    "ollama": ollama.chat,
    "anthropic": anthropic.chat,
}


def chat(settings, system, turns, tools, on_chunk, on_thinking=None):
    name = settings.get("provider", "ollama")
    provider = PROVIDERS.get(name)
    if provider is None:
        raise RuntimeError("Unknown provider '%s'. Pick one of: %s."
                           % (name, ", ".join(sorted(PROVIDERS))))
    return provider(settings, system, turns, tools, on_chunk, on_thinking)
