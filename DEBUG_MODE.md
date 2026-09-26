# Debug mode

Debug mode logs every tool call Claude makes, and a page on localhost shows
them as they happen: which tool, what it was given, what came back, whether
it worked and how long it took. It is off unless you turn it on.

## 1. Start Claude Code with the flag

In a terminal, in your models folder:

```
CLAUDE_FREECAD_DEBUG=1 claude
```

Each tool call is added to a log file in the system's temporary folder,
named after you: `claude-freecad-debug-<your user name>.jsonl`.

## 2. Start the page

In a second terminal, from a copy of this repository:

```
python3 debug_panel.py
```

It reads the same log file, so any copy works. To use another port, add it
at the end: `python3 debug_panel.py 9000`.

## 3. Open the page

Go to http://localhost:8765.

- Each row is one tool call, newest at the top.
- Click a row to see what the tool was given and its full reply.
- Type in the filter box to show one tool.
- Calls from every Claude Code session show here. The session column tells
  them apart.

## Turning it off

Start Claude Code without the flag. Stop the page with Ctrl+C.

## Good to know

- The log keeps growing until you press Clear log on the page. The page
  shows the last 500 calls.
- If no calls appear, Claude Code may not have passed the flag on to the
  plugin. Check that you started it with `CLAUDE_FREECAD_DEBUG=1` in front.
