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
/plugin install claude-freecad-mcp
```

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
