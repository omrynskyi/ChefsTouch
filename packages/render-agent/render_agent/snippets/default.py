from __future__ import annotations

from render_agent.schemas import CSSEntry

# Each entry is one CSS class or data-component declaration.
# page_content = "{name}: {description} | tags: ... | example: ..."
# This is what gets embedded and returned to the agent.

DEFAULT_CSS_ENTRIES: list[CSSEntry] = [

    # ── Cards ────────────────────────────────────────────────────────────────

    CSSEntry(
        name="card",
        description="White rounded card with subtle drop shadow and md padding (16px/24px). Base container for any canvas component.",
        tags=["card", "container", "base", "layout", "surface"],
        example='<div class="card">...</div>',
    ),
    CSSEntry(
        name="card elevated",
        description="Card with a stronger multi-layer shadow and larger radius (20px). Use for the primary focus component — step instructions, main content.",
        tags=["card", "shadow", "elevated", "primary", "focus"],
        example='<div class="card elevated animate-in">...</div>',
    ),
    CSSEntry(
        name="card compact",
        description="Card with reduced padding (10px/16px) and smaller radius (8px). Use for peripheral components: timers, tags, small indicators.",
        tags=["card", "compact", "small", "secondary", "timer"],
        example='<div class="card compact">...</div>',
    ),
    CSSEntry(
        name="card glass",
        description="Frosted-glass card: semi-transparent warm white background with 18px backdrop blur. Use for floating overlays sitting above base content.",
        tags=["card", "glass", "transparent", "blur", "overlay", "float", "frosted"],
        example='<div class="card glass">...</div>',
    ),
    CSSEntry(
        name="card interactive",
        description="Card with pointer cursor, 140ms ease transition, and translateY(-3px) + stronger shadow on hover. Use for tappable recipe cards and selectable options.",
        tags=["card", "interactive", "hover", "clickable", "selectable", "tappable"],
        example='<div class="card interactive">...</div>',
    ),

    # ── Typography ───────────────────────────────────────────────────────────

    CSSEntry(
        name="text-primary",
        description="Dark near-black text (#1c1712), line-height 1.45. Use for the main instruction, title, or any primary-emphasis content.",
        tags=["text", "primary", "content", "high-contrast", "dark"],
        example='<p class="text-primary size-lg">Add the garlic now</p>',
    ),
    CSSEntry(
        name="text-secondary",
        description="Warm medium-brown text (#6b5e4e), line-height 1.45. Use for tips, subtitles, supporting info, quantities.",
        tags=["text", "secondary", "muted", "brown", "tip", "supporting"],
        example='<p class="text-secondary size-sm">Optional: add chilli flakes</p>',
    ),
    CSSEntry(
        name="label-muted",
        description="Tiny uppercase label (11px, 0.09em letter-spacing) in light tan. Block-level with 6px bottom margin. Use for step counters, category eyebrows.",
        tags=["label", "muted", "small", "uppercase", "eyebrow", "step-counter", "category"],
        example='<span class="label-muted">Step 3 of 7</span>',
    ),
    CSSEntry(
        name="font-mono",
        description="Monospace font stack (SF Mono / Fira Code / Menlo). Use for countdown numbers, timer digits, and any numeric display.",
        tags=["font", "monospace", "numbers", "timer", "digits", "countdown"],
        example='<span class="font-mono size-xl">6:00</span>',
    ),
    CSSEntry(
        name="size-sm",
        description="13px font size, line-height 1.5. Use for secondary text, muted labels, ingredient quantities.",
        tags=["size", "small", "font-size", "13px"],
    ),
    CSSEntry(
        name="size-md",
        description="16px font size, line-height 1.5. Default body text size.",
        tags=["size", "medium", "font-size", "16px", "default", "body"],
    ),
    CSSEntry(
        name="size-lg",
        description="22px font size, weight 500, line-height 1.35. Use for primary step instructions and card headings.",
        tags=["size", "large", "font-size", "22px", "instruction", "heading"],
    ),
    CSSEntry(
        name="size-xl",
        description="52px font size, weight 600, line-height 1, negative letter-spacing. Use for countdown timer digits and high-impact numbers.",
        tags=["size", "xl", "font-size", "52px", "timer", "large-number", "countdown"],
    ),

    # ── Animations ───────────────────────────────────────────────────────────

    CSSEntry(
        name="animate-in",
        description="Fade + 10px slide-up entrance animation (180ms ease-out). Apply to any new component entering the canvas.",
        tags=["animation", "enter", "fade", "slide", "transition", "mount"],
        example='<div class="card elevated animate-in">...</div>',
    ),
    CSSEntry(
        name="animate-out",
        description="Fade + 6px slide-down exit animation (150ms ease-in). Apply when a component is dismissed.",
        tags=["animation", "exit", "fade", "transition", "unmount", "dismiss"],
    ),
    CSSEntry(
        name="hover-lift",
        description="translateY(-3px) + stronger shadow on hover, 140ms ease. Use on non-.interactive elements that should signal tappability.",
        tags=["animation", "hover", "lift", "interactive", "transition"],
    ),
    CSSEntry(
        name="pulse-on-end",
        description="Infinite opacity pulse (0.9s, 1→0.35→1). Apply to the timer card container when a countdown reaches zero.",
        tags=["animation", "pulse", "timer", "zero", "alert", "infinite"],
        example='<div class="card compact glass pulse-on-end">...</div>',
    ),

    # ── Timer ────────────────────────────────────────────────────────────────

    CSSEntry(
        name="timer-ring-card",
        description="Donut ring countdown timer. Compact glass card containing an SVG progress ring with the time and label centered inside. Circumference=264 (r=42). Set stroke-dashoffset on timer-ring-progress to show elapsed: 0=full ring, 264=empty ring.",
        tags=["timer", "ring", "donut", "countdown", "circular", "progress", "overlay"],
        example="<div class='card compact glass timer-ring-card animate-in' data-component='timer' data-duration='6m' data-autostart='true' data-label='Chicken'><div class='timer-ring-wrap'><svg class='timer-ring-svg' viewBox='0 0 104 104'><circle class='timer-ring-track' cx='52' cy='52' r='42'/><circle class='timer-ring-progress' cx='52' cy='52' r='42' stroke-dashoffset='106'/></svg><div class='timer-ring-inner'><span class='font-timer'>6:00</span><span class='timer-label'>Chicken</span></div></div></div>",
    ),
    CSSEntry(
        name="font-timer",
        description="Distinctive timer number font: weight 200, 26px, wide letter-spacing, tabular numerals. Use for the countdown digits inside a timer-ring-card.",
        tags=["timer", "font", "light", "number", "display", "thin"],
        example="<span class='font-timer'>6:00</span>",
    ),
    CSSEntry(
        name="timer-label",
        description="Small uppercase label below the timer number. 10px, secondary color. Use for the timer subject (e.g. 'Chicken', 'Rest').",
        tags=["timer", "label", "uppercase", "small", "center"],
        example="<span class='timer-label'>Chicken</span>",
    ),
    CSSEntry(
        name='data-component="timer"',
        description='Initializes a live countdown timer. Required: data-duration (e.g. "6m", "1m30s"), data-autostart ("true"/"false"), data-label (display label). Use inside timer-ring-card.',
        tags=["timer", "countdown", "interactive", "behavior", "component", "data-component"],
        example="<div class='card compact glass timer-ring-card' data-component='timer' data-duration='6m' data-autostart='true' data-label='Chicken'>",
    ),

    # ── Alert / warning ──────────────────────────────────────────────────────

    CSSEntry(
        name="alert",
        description="Top-zone warning strip: warm amber background, 3px left accent border, padded. Use for time-sensitive cooking warnings.",
        tags=["alert", "warning", "top", "prominent", "danger", "strip"],
        example='<div class="alert animate-in" zone="top" size="medium" layer="float">Watch the heat</div>',
    ),
    CSSEntry(
        name="alert alert-urgent",
        description="Alert variant with terracotta-tinted background and accent text. Use when the warning needs stronger emphasis.",
        tags=["alert", "urgent", "critical", "warning", "accent"],
        example='<div class="alert alert-urgent animate-in" zone="top" size="medium" layer="float">Burning risk!</div>',
    ),

    # ── Progress bar ─────────────────────────────────────────────────────────

    CSSEntry(
        name="progress-bar",
        description="Wrapper for step progress indicator. Full-width block. Contains a .label-muted eyebrow and a .progress-track.",
        tags=["progress", "steps", "navigation", "wrapper"],
        example='<div class="progress-bar card compact" zone="top" size="medium" layer="base">...</div>',
    ),
    CSSEntry(
        name="progress-track",
        description="6px pill-shaped track (warm gray background). Wrap inside .progress-bar. Child: .progress-fill.",
        tags=["progress", "track", "bar", "background", "pill"],
        example='<div class="progress-track"><div class="progress-fill" style="width:40%"></div></div>',
    ),
    CSSEntry(
        name="progress-fill",
        description="Terracotta-colored fill bar inside .progress-track. Set width via inline style (e.g. style=\"width:40%\"). Animates width transitions at 400ms.",
        tags=["progress", "fill", "accent", "width", "animated"],
        example='<div class="progress-fill" style="width:40%"></div>',
    ),
    CSSEntry(
        name='data-component="progress"',
        description="Step progress indicator bar. Required: data-current (current step number), data-total (total steps). Renders track + fill automatically.",
        tags=["progress", "steps", "navigation", "bar", "indicator", "component", "data-component"],
        example='<div class="card compact" data-component="progress" data-current="1" data-total="6"></div>',
    ),

    # ── Recipe selection ─────────────────────────────────────────────────────

    CSSEntry(
        name="recipe-grid",
        description="3-column equal-width grid (gap 16px) for recipe selection cards. Fills full width. Direct children should be .recipe-option.",
        tags=["recipe", "grid", "3-column", "selection", "layout"],
        example='<div class="recipe-grid">...</div>',
    ),
    CSSEntry(
        name="recipe-option",
        description="Tappable recipe card inside .recipe-grid. White background, md radius, column flex layout, hover lift. Fire data-component action-btn on tap.",
        tags=["recipe", "card", "option", "tappable", "selectable", "interactive"],
        example='<div class="recipe-option" data-component="action-btn" data-action="select_recipe_1">...</div>',
    ),
    CSSEntry(
        name="recipe-title",
        description="16px semibold dark title inside a .recipe-option card. Use for the recipe name.",
        tags=["recipe", "title", "heading", "bold"],
        example='<p class="recipe-title">Aglio e Olio</p>',
    ),
    CSSEntry(
        name="recipe-meta",
        description="13px secondary-color description or metadata inside a .recipe-option. Use for cook time, difficulty, or short description.",
        tags=["recipe", "meta", "description", "secondary", "small"],
        example='<p class="recipe-meta">20 min · Easy</p>',
    ),

    # ── Ingredients list ─────────────────────────────────────────────────────

    CSSEntry(
        name="ingredient-list",
        description="Scrollable flex column for ingredient rows. Max-height 340px with thin scrollbar. Wrap .ingredient-row items inside.",
        tags=["ingredient", "list", "scroll", "column", "layout"],
        example='<div class="ingredient-list">...</div>',
    ),
    CSSEntry(
        name="ingredient-row",
        description="Single ingredient row with space-between flex layout. Subtle bottom border. Contains .ingredient-name (left) and .ingredient-qty (right).",
        tags=["ingredient", "row", "flex", "name", "quantity"],
        example='<div class="ingredient-row"><span class="ingredient-name">Garlic</span><span class="ingredient-qty">3 cloves</span></div>',
    ),
    CSSEntry(
        name="ingredient-name",
        description="15px primary-color ingredient name, left side of .ingredient-row.",
        tags=["ingredient", "name", "text", "primary"],
        example='<span class="ingredient-name">Garlic</span>',
    ),
    CSSEntry(
        name="ingredient-qty",
        description="14px secondary-color quantity/measure, right side of .ingredient-row. Tabular numerals, no-wrap.",
        tags=["ingredient", "quantity", "measure", "secondary", "right"],
        example='<span class="ingredient-qty">3 cloves</span>',
    ),

    # ── Suggestion card ──────────────────────────────────────────────────────

    CSSEntry(
        name="suggestion-card",
        description="Bottom-zone suggestion layout: full-width column — label and text stacked on top, dismiss button full-width below. Use with card glass. Inner elements: suggestion-body (full width), suggestion-text (body text), suggestion-action (full-width button at bottom).",
        tags=["suggestion", "bottom", "flex", "row", "dismiss", "proactive", "layout"],
        example="<div class='card glass suggestion-card animate-in' zone='bottom' size='medium' layer='float'><div class='suggestion-body'><span class='label-muted'>While you wait</span><p class='text-primary size-md suggestion-text'>You could chop the garlic now.</p></div><button class='card compact interactive suggestion-action' data-component='action-btn' data-action='dismiss_suggestion'>Dismiss</button></div>",
    ),

    # ── Tags / pills ─────────────────────────────────────────────────────────

    CSSEntry(
        name="tag",
        description="Small pill label: warm gray background, 12px medium weight, secondary text, full-border-radius. Use for category and metadata chips.",
        tags=["tag", "pill", "label", "badge", "category", "chip"],
        example='<span class="tag">italian</span>',
    ),
    CSSEntry(
        name="tag-row",
        description="Flex wrap row with 6px gap and 10px top margin for groups of .tag pills.",
        tags=["tag", "row", "flex", "tags", "pills", "group"],
        example='<div class="tag-row"><span class="tag">italian</span><span class="tag">30 min</span></div>',
    ),

    # ── Utility ──────────────────────────────────────────────────────────────

    CSSEntry(
        name="muted",
        description="Sets opacity to 0.45. Layer over any element to de-emphasize it. Combine with .text-secondary for strongly subordinate content.",
        tags=["muted", "opacity", "dim", "secondary", "de-emphasize"],
    ),
    CSSEntry(
        name="divider",
        description="Full-width 1px horizontal rule in border-subtle color with 16px vertical margin. Use to separate sections inside a card.",
        tags=["divider", "separator", "rule", "line", "section"],
        example='<hr class="divider" />',
    ),
    CSSEntry(
        name="btn-primary",
        description="Terracotta-filled CTA button (background var(--accent)), white text, 600 weight, sm radius. Use for the primary action in a card.",
        tags=["button", "primary", "cta", "accent", "terracotta", "action"],
        example='<button class="btn-primary" data-component="action-btn" data-action="next_step">Next step</button>',
    ),

    # ── Interactive components ────────────────────────────────────────────────

    CSSEntry(
        name='data-component="camera"',
        description="Triggers camera capture. Captures 3 frames then closes. Required: data-prompt (analysis context string).",
        tags=["camera", "capture", "vision", "photo", "analyze", "component", "data-component"],
        example='<div class="card elevated animate-in" data-component="camera" data-prompt="Is this cooked?">',
    ),
    CSSEntry(
        name='data-component="action-btn"',
        description="Fires a named action to the parent app. Required: data-action (action name string). Apply to any button or interactive card.",
        tags=["button", "action", "interactive", "tap", "trigger", "component", "data-component"],
        example='<button class="card interactive" data-component="action-btn" data-action="next_step">Next</button>',
    ),
]


DEFAULT_SNIPPETS = [entry.to_document() for entry in DEFAULT_CSS_ENTRIES]
