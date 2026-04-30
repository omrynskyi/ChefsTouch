from __future__ import annotations

import bleach

ALLOWED_TAGS = [
    "div", "span", "p", "h1", "h2", "h3", "h4",
    "ul", "ol", "li", "img", "button", "hr",
    "svg", "circle",
]

ALLOWED_ATTRIBUTES: dict = {
    "*": [
        "class", "id", "zone", "size", "layer",
        "style",
        "data-component", "data-duration", "data-autostart", "data-label",
        "data-prompt", "data-action", "data-current", "data-total",
        "data-default", "aria-label", "role",
    ],
    "svg": ["viewBox", "xmlns", "width", "height"],
    "circle": ["cx", "cy", "r", "stroke-dasharray", "stroke-dashoffset"],
}


def sanitize_html(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
