#!/usr/bin/env python3
"""A page on localhost that shows every tool call as it happens.

    python3 debug_panel.py [port]        default port 8765

Reads the log the MCP server writes when CLAUDE_FREECAD_DEBUG=1 (see
ai_cad/debug.py). It runs on its own, not inside the MCP server, so a port
already in use can never stop the server -- and every Claude Code session
writes to the one log, so one page shows them all.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

from ai_cad import debug                     # noqa: E402  (needs the path above)

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>FreeCAD tool calls</title>
<style>
  :root { color-scheme: light dark; --line: #8884; --bad: #d33; --good: #2a2; }
  body { font: 14px system-ui, sans-serif; margin: 0; padding: 16px; }
  header { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
  h1 { font-size: 18px; margin: 0; flex: 1; }
  input { font: inherit; padding: 4px 8px; }
  button { font: inherit; padding: 4px 12px; cursor: pointer; }
  .note { opacity: .7; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { font-weight: 600; }
  tr.row { cursor: pointer; }
  tr.row:hover { background: #8881; }
  .ok { color: var(--good); } .fail { color: var(--bad); font-weight: 600; }
  .num { font-variant-numeric: tabular-nums; }
  pre { margin: 4px 0 8px; white-space: pre-wrap; word-break: break-word; font-size: 13px; }
  .label { font-weight: 600; margin-top: 4px; }
</style>
<header>
  <h1>FreeCAD tool calls</h1>
  <input id="filter" placeholder="Filter by tool">
  <button id="clear">Clear log</button>
</header>
<p class="note" id="status"></p>
<table>
  <thead><tr><th>Time</th><th>Session</th><th>Tool</th><th>Result</th><th class="num">Seconds</th></tr></thead>
  <tbody id="rows"></tbody>
</table>
<script>
const open = new Set();
let entries = [];

function esc(s) {
  return String(s).replace(/[&<>]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
}

function render() {
  const filter = document.getElementById("filter").value.trim().toLowerCase();
  const shown = entries.filter(e => !filter || String(e.tool).toLowerCase().includes(filter));
  document.getElementById("status").textContent = entries.length
    ? shown.length + " of " + entries.length + " calls. Click a row for its inputs and reply."
    : "No calls yet. Start Claude Code with CLAUDE_FREECAD_DEBUG=1 and use a FreeCAD tool.";
  document.getElementById("rows").innerHTML = shown.slice().reverse().map(e => {
    const key = e.session + ":" + e.time;
    const row = "<tr class='row' data-key='" + key + "'><td class='num'>" +
      new Date(e.time * 1000).toLocaleTimeString() + "</td><td class='num'>" + e.session +
      "</td><td>" + esc(e.tool) + "</td><td class='" + (e.ok ? "ok'>worked" : "fail'>failed") +
      "</td><td class='num'>" + e.seconds + "</td></tr>";
    if (!open.has(key)) return row;
    return row + "<tr><td colspan='5'><div class='label'>Inputs</div><pre>" +
      esc(JSON.stringify(e.arguments, null, 2)) + "</pre><div class='label'>Reply</div><pre>" +
      esc(e.reply) + "</pre></td></tr>";
  }).join("");
}

document.getElementById("rows").addEventListener("click", ev => {
  const row = ev.target.closest("tr.row");
  if (!row) return;
  const key = row.dataset.key;
  open.has(key) ? open.delete(key) : open.add(key);
  render();
});
document.getElementById("filter").addEventListener("input", render);
document.getElementById("clear").addEventListener("click", async () => {
  await fetch("/clear", {method: "POST"});
  entries = [];
  render();
});

async function poll() {
  try {
    const fresh = await (await fetch("/log")).json();
    if (JSON.stringify(fresh) !== JSON.stringify(entries)) { entries = fresh; render(); }
  } catch (err) {
    document.getElementById("status").textContent = "Lost the panel: is debug_panel.py still running?";
  }
  setTimeout(poll, 1000);
}
render();
poll();
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, kind):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/log":
            self._send(json.dumps(debug.read()), "application/json")
        else:
            self._send(PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        if self.path == "/clear":
            debug.clear()
        self._send("{}", "application/json")

    def log_message(self, *_):
        pass          # the page polls every second; don't fill the terminal


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Debug panel: http://localhost:%d" % port)
    print("Reading %s" % debug.log_path())
    if not debug.enabled():
        print("Note: start Claude Code with CLAUDE_FREECAD_DEBUG=1, or nothing is logged.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
