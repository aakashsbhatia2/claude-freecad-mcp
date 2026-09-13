# Installing

## Requirements

- FreeCAD 1.0 or newer
- Claude Code
- Linux or macOS

## 1. Install the add-on

Open Edit, then Preferences, then Addon Manager. Under Custom repositories,
add one:

- Repository URL: `https://github.com/aakashsbhatia2/claude-freecad-mcp`
- Branch: `main`

Then open Tools, then Addon Manager. claude-freecad-mcp is now in the list.
Install it and restart FreeCAD. Uninstalling later is in the same place.

## 2. Add it to Claude Code

Type these into Claude Code:

```
/plugin marketplace add aakashsbhatia2/claude-freecad-mcp
/plugin install claude-freecad-mcp --scope local
```

The plugin stops Claude Code from working around its FreeCAD tools. While it
is on, Claude Code cannot run shell commands or write and edit files, apart
from .html pages for artifacts. That keeps the results predictable, but it
would get in the way of any other work.

So install it with `--scope local`. That turns it on in the folder you are
in and nowhere else. Run it from your models folder. Leave the scope off and
it turns on in every project you open, blocking those tools there too.

To remove it later, in a terminal in that same folder:

```
claude plugin uninstall claude-freecad-mcp@claude-freecad-mcp --scope local
```

The scope has to match the one you installed with, or it looks in the wrong
place and reports nothing to remove.

To update to a newer version, in a terminal in that same folder:

```
claude plugin marketplace update claude-freecad-mcp
claude plugin update claude-freecad-mcp@claude-freecad-mcp --scope local
```

The first line matters. Claude Code keeps its own copy of the plugin list
and does not refresh it by itself, so without it the update finds nothing
new. Then restart Claude Code: a session that is already open keeps the old
version until it is started again. `claude --continue` picks up where you
left off.

## 3. Use it

Open FreeCAD. Then run `claude` in your models folder. `/mcp` confirms it
found FreeCAD.

Keep both windows open.

Ask for what you want and it builds it.

Some things need you to say which face or edge you mean — a fillet, a hole,
a sketch on a face. Click it in FreeCAD, then ask.

## The status line

Bottom right of the FreeCAD window:

```
Claude Code | connected | last: pad | selected: Pad Face3
```

Whether Claude Code is attached, the last tool that ran, and what it can see
you have clicked. Reads `no client` when nothing is connected.
