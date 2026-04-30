"""
Canvas preview: writes current canvas state to /tmp/canvas_preview.html
and opens it in the browser. The page auto-refreshes every second.

Reads design-system.css from apps/web/public/ (relative to repo root)
so the preview always matches the iframe sandbox styles.
"""

from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Dict, Any

PREVIEW_PATH = "/tmp/canvas_preview.html"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CSS_PATH = _REPO_ROOT / "apps" / "web" / "public" / "design-system.css"


def _load_css() -> str:
    if _CSS_PATH.exists():
        return _CSS_PATH.read_text()
    return "/* design-system.css not found */"


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
        components = (
            '    <div zone="center" size="medium" layer="base" '
            'style="opacity:0.3; display:flex; align-items:center; '
            'justify-content:center; color:#a89880; font-size:14px;">canvas empty</div>'
        )
    else:
        components = "\n".join(
            f"    {comp['html']}"
            for comp in canvas_state.values()
            if comp.get("html")
        )

    html = HTML_TEMPLATE.format(css=_load_css(), components=components)

    with open(PREVIEW_PATH, "w") as f:
        f.write(html)

    if not _opened:
        webbrowser.open(f"file://{PREVIEW_PATH}")
        _opened = True
