"""
Canvas preview: writes current canvas state to /tmp/canvas_preview.html
and opens it in the browser. The page auto-refreshes every second.
"""

from __future__ import annotations

import os
import webbrowser
from typing import Dict, Any

PREVIEW_PATH = "/tmp/canvas_preview.html"

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0f0f0f;
  color: #f0f0f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  height: 100vh;
  overflow: hidden;
}

/* ── Grid ────────────────────────────────────────────────────── */
.canvas-grid {
  display: grid;
  width: 100vw;
  height: 100vh;
  grid-template-columns: 140px 1fr 140px;
  grid-template-rows: 72px 1fr 72px;
  grid-template-areas:
    "corner-tl   top      corner-tr"
    "left        center   right"
    "corner-bl   bottom   corner-br";
}

[zone="center"]    { grid-area: center;    display: flex; align-items: center; justify-content: center; padding: 24px; }
[zone="top"]       { grid-area: top;       display: flex; align-items: center; justify-content: center; padding: 8px 16px; }
[zone="bottom"]    { grid-area: bottom;    display: flex; align-items: center; justify-content: center; padding: 8px 16px; }
[zone="left"]      { grid-area: left;      display: flex; align-items: center; justify-content: center; padding: 8px; }
[zone="right"]     { grid-area: right;     display: flex; align-items: center; justify-content: center; padding: 8px; }
[zone="corner-tl"] { grid-area: corner-tl; display: flex; align-items: flex-start; justify-content: flex-start; padding: 10px; }
[zone="corner-tr"] { grid-area: corner-tr; display: flex; align-items: flex-start; justify-content: flex-end;   padding: 10px; }
[zone="corner-bl"] { grid-area: corner-bl; display: flex; align-items: flex-end;   justify-content: flex-start; padding: 10px; }
[zone="corner-br"] { grid-area: corner-br; display: flex; align-items: flex-end;   justify-content: flex-end;   padding: 10px; }

[layer="base"]  { z-index: 1; }
[layer="float"] { z-index: 10; pointer-events: auto; }

[size="small"]  { max-width: 220px; }
[size="medium"] { max-width: 420px; }
[size="large"]  { max-width: 680px; width: 100%; }

/* ── Cards ───────────────────────────────────────────────────── */
.card {
  background: #1c1c1e;
  border-radius: 16px;
  padding: 20px 24px;
  border: 1px solid rgba(255,255,255,0.07);
  width: 100%;
}
.card.elevated  { box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
.card.compact   { padding: 12px 16px; border-radius: 12px; }
.card.glass     { background: rgba(255,255,255,0.07); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.12); }
.card.interactive { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
.card.interactive:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.6); }

/* ── Typography ──────────────────────────────────────────────── */
.text-primary   { color: #f0f0f0; line-height: 1.4; }
.text-secondary { color: #a0a0a0; line-height: 1.4; }
.label-muted    { color: #666; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; display: block; margin-bottom: 6px; }
.font-mono      { font-family: 'SF Mono', 'Fira Code', monospace; }
.muted          { opacity: 0.5; }

.size-sm  { font-size: 13px; }
.size-md  { font-size: 16px; }
.size-lg  { font-size: 22px; font-weight: 500; }
.size-xl  { font-size: 48px; font-weight: 600; line-height: 1; }

/* ── Timer ───────────────────────────────────────────────────── */
.timer-display { display: block; }

/* ── Tags ────────────────────────────────────────────────────── */
.tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.tag     { background: rgba(255,255,255,0.08); border-radius: 20px; padding: 3px 10px; font-size: 12px; color: #a0a0a0; }

/* ── Animations ──────────────────────────────────────────────── */
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeSlideIn 0.15s ease-out forwards; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
.pulse-on-end { animation: pulse 1s ease-in-out infinite; }

/* ── Layout helpers ──────────────────────────────────────────── */
ul, ol { padding-left: 20px; }
li     { margin-bottom: 6px; }
h1, h2, h3 { font-weight: 600; line-height: 1.2; margin-bottom: 8px; }
p + p  { margin-top: 8px; }
button { background: rgba(255,255,255,0.1); border: none; color: inherit; border-radius: 8px; padding: 8px 16px; font-size: 14px; cursor: pointer; }
button:hover { background: rgba(255,255,255,0.18); }
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="1">
  <title>Canvas Preview</title>
  <style>{css}</style>
</head>
<body>
  <div class="canvas-grid">
{components}
  </div>
</body>
</html>"""

_opened = False


def render(canvas_state: Dict[str, Any]) -> None:
    global _opened

    if not canvas_state:
        components = '    <div zone="center" size="medium" layer="base" style="opacity:0.2; display:flex; align-items:center; justify-content:center; color:#666; font-size:14px;">canvas empty</div>'
    else:
        components = "\n".join(
            f"    {comp['html']}"
            for comp in canvas_state.values()
            if comp.get("html")
        )

    html = HTML_TEMPLATE.format(css=CSS, components=components)

    with open(PREVIEW_PATH, "w") as f:
        f.write(html)

    if not _opened:
        webbrowser.open(f"file://{PREVIEW_PATH}")
        _opened = True
