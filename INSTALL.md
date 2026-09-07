# Installing

## Requirements

- FreeCAD 1.0 or newer
- Claude Code
- Linux or macOS

## 1. Install the add-on

Open Edit, then Preferences, then Addon Manager. Under Custom repositories,
add one:

- Repository URL: `https://github.com/aakashsbhatia2/conversational-free-cad-plugin`
- Branch: `main`

Then open Tools, then Addon Manager. claude-freecad-mcp is now in the list.
Install it and restart FreeCAD. Uninstalling later is in the same place.

## 2. Add it to Claude Code

Type these into Claude Code:

```
/plugin marketplace add aakashsbhatia2/conversational-free-cad-plugin
/plugin install claude-freecad-mcp
```

If Claude Code asks permission before every tool, put this in
`~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["mcp__plugin_claude-freecad-mcp_freecad__.*"]
  }
}
```

## 3. Use it

Open FreeCAD. Then run `claude` in your models folder. `/mcp` confirms it
found FreeCAD.

Keep both windows open.

To work on something you can see, click the face or edge in FreeCAD first,
then ask.

## The status line

Bottom right of the FreeCAD window:

```
Claude Code | connected | last: pad | selected: Pad Face3
```

Whether Claude Code is attached, the last tool that ran, and what it can see
you have clicked. Reads `no client` when nothing is connected.

## When it doesn't work

Check FreeCAD and Claude Code are both running and the status line says
`connected`.

If the status line is missing entirely, the add-on did not load. Look in
View, Panels, Report view for the reason.

## Limits

No screenshots. The result can only be read back through the tools.

No headless mode. FreeCAD must be running with its window open.

No Windows.

One call at a time. A call arriving while a FreeCAD dialog is open waits until
the dialog closes, and returns an error after two minutes.
