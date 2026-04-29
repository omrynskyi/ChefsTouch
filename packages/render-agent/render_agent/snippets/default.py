from __future__ import annotations

from render_agent.schemas import CSSEntry

# Each entry is one CSS class or data-component declaration.
# page_content = "{name}: {description} | tags: ... | example: ..."
# This is what gets embedded and returned to the agent.

DEFAULT_CSS_ENTRIES: list[CSSEntry] = [

    # ── Cards ────────────────────────────────────────────────────────────────

    CSSEntry(
        name="card",
        description="Base card container. Rounded corners, background fill, padding. Wrap any contained UI element.",
        tags=["card", "container", "base", "layout"],
        example='<div class="card">...</div>',
    ),
    CSSEntry(
        name="card elevated",
        description="Card with drop shadow. Use for primary focus components on the canvas.",
        tags=["card", "shadow", "elevated", "primary"],
        example='<div class="card elevated">...</div>',
    ),
    CSSEntry(
        name="card compact",
        description="Card with reduced padding. Use for smaller secondary components like timers.",
        tags=["card", "compact", "small", "secondary"],
        example='<div class="card compact">...</div>',
    ),
    CSSEntry(
        name="card glass",
        description="Card with semi-transparent background and blur. Use for floating overlays that sit above base content.",
        tags=["card", "glass", "transparent", "blur", "overlay", "float"],
        example='<div class="card glass">...</div>',
    ),
    CSSEntry(
        name="card interactive",
        description="Card that responds to hover and focus. Use for tappable/clickable cards like recipe options.",
        tags=["card", "interactive", "hover", "clickable", "selectable"],
        example='<div class="card interactive">...</div>',
    ),

    # ── Typography ───────────────────────────────────────────────────────────

    CSSEntry(
        name="text-primary",
        description="Primary content text. High contrast. Use for the main instruction or title.",
        tags=["text", "primary", "content", "high-contrast"],
        example='<p class="text-primary size-lg">Main instruction</p>',
    ),
    CSSEntry(
        name="text-secondary",
        description="Secondary content text. Medium contrast. Use for tips, subtitles, or supporting info.",
        tags=["text", "secondary", "muted", "tip", "supporting"],
        example='<p class="text-secondary size-sm">Optional tip</p>',
    ),
    CSSEntry(
        name="label-muted",
        description="Small uppercase label with low contrast and letter spacing. Use for step counters, category labels.",
        tags=["label", "muted", "small", "uppercase", "step-counter"],
        example='<span class="label-muted">Step 3 of 7</span>',
    ),
    CSSEntry(
        name="font-mono",
        description="Monospace font. Use for numbers, timers, and code-like values.",
        tags=["font", "monospace", "numbers", "timer", "digits"],
        example='<span class="font-mono size-xl">6:00</span>',
    ),
    CSSEntry(
        name="size-sm",
        description="Small font size. Use for secondary text, labels, and tips.",
        tags=["size", "small", "font-size"],
    ),
    CSSEntry(
        name="size-md",
        description="Medium font size. Default body text.",
        tags=["size", "medium", "font-size", "default"],
    ),
    CSSEntry(
        name="size-lg",
        description="Large font size. Use for primary step instructions.",
        tags=["size", "large", "font-size", "prominent"],
    ),
    CSSEntry(
        name="size-xl",
        description="Extra large font size. Use for timer displays and high-impact numbers.",
        tags=["size", "xl", "font-size", "timer", "large-number"],
    ),

    # ── Animations ───────────────────────────────────────────────────────────

    CSSEntry(
        name="animate-in",
        description="Fade and slide in on mount (150ms). Apply to new components entering the canvas.",
        tags=["animation", "enter", "fade", "transition", "mount"],
        example='<div class="card elevated animate-in">...</div>',
    ),
    CSSEntry(
        name="animate-out",
        description="Fade and slide out on unmount (150ms). Apply when a component is being dismissed.",
        tags=["animation", "exit", "fade", "transition", "unmount"],
    ),
    CSSEntry(
        name="hover-lift",
        description="Subtle translateY on hover. Use on interactive cards to signal tappability.",
        tags=["animation", "hover", "lift", "interactive"],
    ),
    CSSEntry(
        name="pulse-on-end",
        description="Pulsing animation triggered when a timer reaches zero. Apply to the timer container.",
        tags=["animation", "pulse", "timer", "zero", "alert"],
        example='<div class="card compact glass pulse-on-end">...</div>',
    ),

    # ── Timer component ──────────────────────────────────────────────────────

    CSSEntry(
        name="timer-display",
        description="Large prominent number display for countdowns. Combine with font-mono and size-xl.",
        tags=["timer", "countdown", "display", "number"],
        example='<span class="timer-display font-mono size-xl">6:00</span>',
    ),
    CSSEntry(
        name='data-component="timer"',
        description='Initializes a countdown timer. Required data attributes: data-duration (e.g. "6m", "1m30s"), data-autostart ("true"/"false"), data-label (display label).',
        tags=["timer", "countdown", "interactive", "behavior", "component"],
        example='<div class="card compact glass" data-component="timer" data-duration="6m" data-autostart="true" data-label="Chicken">',
    ),

    # ── Camera component ─────────────────────────────────────────────────────

    CSSEntry(
        name='data-component="camera"',
        description="Triggers camera capture. Captures 3 frames automatically then closes. Required: data-prompt (analysis context string).",
        tags=["camera", "capture", "vision", "photo", "analyze", "component"],
        example='<div class="card elevated animate-in" data-component="camera" data-prompt="Is this cooked?">',
    ),

    # ── Action button ────────────────────────────────────────────────────────

    CSSEntry(
        name='data-component="action-btn"',
        description="Button that fires a named action to the parent app. Required: data-action (action name string).",
        tags=["button", "action", "interactive", "tap", "trigger", "component"],
        example='<button class="card interactive" data-component="action-btn" data-action="next_step">Next</button>',
    ),

    # ── Progress component ───────────────────────────────────────────────────

    CSSEntry(
        name='data-component="progress"',
        description="Step progress indicator bar. Required: data-current (current step number), data-total (total steps).",
        tags=["progress", "steps", "navigation", "bar", "indicator", "component"],
        example='<div class="card compact" data-component="progress" data-current="1" data-total="6"></div>',
    ),

    # ── Tags / pills ─────────────────────────────────────────────────────────

    CSSEntry(
        name="tag",
        description="Small pill label. Use inside tag-row for category or metadata labels.",
        tags=["tag", "pill", "label", "badge", "category"],
        example='<span class="tag">italian</span>',
    ),
    CSSEntry(
        name="tag-row",
        description="Horizontal flex row of tag pills. Wrap multiple tag elements inside.",
        tags=["tag", "row", "flex", "tags", "pills"],
        example='<div class="tag-row"><span class="tag">italian</span></div>',
    ),
    CSSEntry(
        name="muted",
        description="Reduces opacity of the element. Combine with text-secondary for de-emphasized content.",
        tags=["muted", "opacity", "dim", "secondary"],
    ),
]


DEFAULT_SNIPPETS = [entry.to_document() for entry in DEFAULT_CSS_ENTRIES]
