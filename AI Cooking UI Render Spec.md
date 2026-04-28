
# AI Cooking Assistant — Rendering Architecture Spec

**Version:** 0.1  
**Author:** Oleg Mrynskyi  
**Status:** Draft  
**Last Updated:** April 2026

---

## Overview

This document specifies the rendering architecture for the agent-controlled canvas. It covers how the agent generates UI, how that UI is safely executed in the browser, and how the three layers of the rendering system work together.

This architecture is designed to be general purpose. The cooking app is the first implementation but the pattern — agent-generated HTML constrained by a design system, positioned via named grid zones, with interactivity driven by a sandboxed runtime registry — applies to any AI-driven web interface.

---

## Core Principle

The agent generates HTML. It never generates CSS implementations, JavaScript behavior, or layout math. Three separate layers own those concerns and the agent only knows the vocabulary of each layer, not the implementation.

```
Agent output         →    HTML + class names + zone attributes + data-component attributes
Style layer          →    CSS design system injected into iframe
Positioning layer    →    Named CSS grid areas injected into iframe  
Behavior layer       →    Runtime registry injected into iframe
```

The agent's complete vocabulary is: class names retrieved from vector search, zone names (8 tokens), size values (3 tokens), layer values (2 tokens), and component names from the runtime registry. Everything else is handled by the renderer.

---

## Layer 1 — Style (CSS Design System)

### How it works

A curated set of CSS classes is maintained as a design system. The full class list is never loaded into the agent context at once. Instead the design system is stored as a vector index of **component snippets**. Before each agent turn the current context is embedded and the top 5 most relevant snippets are retrieved and injected into the system prompt.

The agent generates HTML using only classes from the retrieved snippets. It never invents class names.

### Snippet format

Each entry in the vector index is a self-contained HTML snippet with inline documentation comments. The snippet is the embedding unit, not individual class names.

```html
<!-- SNIPPET: step-instruction -->
<!-- USE FOR: displaying the current cooking step as the primary focus -->
<!-- TAGS: step, instruction, cooking, primary, focus -->
<div class="card elevated animate-in">
  <span class="label-muted">Step 3 of 7</span>
  <p class="text-primary size-lg">Your instruction here</p>
  <p class="text-secondary size-sm muted">Optional tip here</p>
</div>
```

```html
<!-- SNIPPET: timer-compact -->
<!-- USE FOR: showing a countdown timer as a secondary floating element -->
<!-- TAGS: timer, countdown, float, secondary -->
<div class="card compact glass pulse-on-end">
  <span class="timer-display font-mono size-xl">6:00</span>
  <span class="label-muted">Label here</span>
</div>
```

```html
<!-- SNIPPET: recipe-option -->
<!-- USE FOR: presenting a single recipe choice the user can select -->
<!-- TAGS: recipe, card, selection, choice -->
<div class="card interactive hover-lift">
  <p class="text-primary size-md">Recipe title</p>
  <p class="text-secondary size-sm muted">25 min · Easy</p>
  <div class="tag-row">
    <span class="tag">italian</span>
    <span class="tag">pasta</span>
  </div>
</div>
```

### Snippet index

| Snippet ID | Description | Tags |
|------------|-------------|------|
| `step-instruction` | Current cooking step, primary focus | step, instruction, primary |
| `step-tip` | Secondary tip below a step | tip, secondary, hint |
| `recipe-option` | Single selectable recipe card | recipe, card, selection |
| `recipe-list` | Container for multiple recipe options | recipe, list, grid |
| `timer-compact` | Floating countdown timer | timer, float, compact |
| `timer-large` | Full-size centered timer | timer, large, primary |
| `camera-frame` | Camera capture view | camera, capture, input |
| `suggestion-card` | Proactive parallel task suggestion | suggestion, proactive, hint |
| `text-response` | Short freeform agent text | text, response, message |
| `progress-bar` | Step progress indicator | progress, steps, nav |
| `ingredient-list` | List of ingredients with quantities | ingredients, list, prep |
| `alert-warning` | Warning or correction message | alert, warning, feedback |
| `alert-success` | Positive feedback message | alert, success, feedback |

### Core class reference

The following classes are always available in the iframe stylesheet regardless of retrieval. They cover base primitives the agent can always rely on.

**Cards**
```
card          base card container, rounded corners, background fill, padding
card.elevated adds drop shadow
card.compact  reduced padding for smaller components
card.glass    semi-transparent background with blur
card.interactive adds cursor pointer and focus ring
```

**Typography**
```
text-primary     primary content text, high contrast
text-secondary   secondary content text, medium contrast
label-muted      small label, low contrast, uppercase tracking
font-mono        monospace font for numbers and code
size-sm / size-md / size-lg / size-xl   font size scale
```

**Layout utilities**
```
animate-in       fade + slide in on mount (150ms)
animate-out      fade + slide out on unmount (150ms)
hover-lift       subtle translateY on hover for interactive cards
pulse-on-end     pulses element when a timer reaches zero
tag              small pill label
tag-row          horizontal flex row of tags
```

**Timer specific**
```
timer-display    large prominent number display
pulse-on-end     animation class applied at zero
```

### Vector retrieval pipeline

```
1. Embed current turn context
   input: "{user_message} | active_recipe: {title} | current_step: {n} | canvas: {component_ids}"

2. Query pgvector index
   SELECT snippet_html, snippet_id, description
   FROM design_snippets
   ORDER BY embedding <=> query_embedding
   LIMIT 5

3. Inject retrieved snippets into system prompt
   "You have access to the following UI snippets. Use only these class names in your HTML output."
   [snippet 1]
   [snippet 2]
   ...

4. Agent generates HTML using retrieved classes
```

### Embedding model

`all-MiniLM-L6-v2` via `sentence-transformers` in the FastAPI backend. No external API key required. Runs on CPU. Embeddings are generated at snippet index build time, not at query time.

---

## Layer 2 — Positioning (Named CSS Grid Zones)

### How it works

The canvas is a CSS grid with named areas. Every iframe shares the same base grid layout injected via the iframe stylesheet. The agent positions components by writing a `zone` attribute on the root element of each component. The iframe stylesheet maps zone names to grid areas.

The agent never writes flexbox rules, absolute coordinates, or translate values.

### Zone vocabulary

The agent knows exactly 8 zone names:

```
center       Main content area, largest zone, primary focus
top          Horizontal strip at the top of the canvas
bottom       Horizontal strip at the bottom of the canvas
left         Vertical strip on the left
right        Vertical strip on the right
corner-tl    Small floating zone, top left
corner-tr    Small floating zone, top right
corner-bl    Small floating zone, bottom left
corner-br    Small floating zone, bottom right
```

### Grid definition

```css
.canvas-grid {
  display: grid;
  width: 100vw;
  height: 100vh;
  grid-template-columns: 120px 1fr 120px;
  grid-template-rows: 80px 1fr 80px;
  grid-template-areas:
    "corner-tl   top      corner-tr"
    "left        center   right"
    "corner-bl   bottom   corner-br";
  position: relative;
}

[zone="center"]    { grid-area: center; display: flex; align-items: center; justify-content: center; }
[zone="top"]       { grid-area: top; display: flex; align-items: center; justify-content: center; }
[zone="bottom"]    { grid-area: bottom; display: flex; align-items: center; justify-content: center; }
[zone="left"]      { grid-area: left; display: flex; align-items: center; justify-content: center; }
[zone="right"]     { grid-area: right; display: flex; align-items: center; justify-content: center; }
[zone="corner-tl"] { grid-area: corner-tl; display: flex; align-items: flex-start; justify-content: flex-start; padding: 8px; }
[zone="corner-tr"] { grid-area: corner-tr; display: flex; align-items: flex-start; justify-content: flex-end; padding: 8px; }
[zone="corner-bl"] { grid-area: corner-bl; display: flex; align-items: flex-end; justify-content: flex-start; padding: 8px; }
[zone="corner-br"] { grid-area: corner-br; display: flex; align-items: flex-end; justify-content: flex-end; padding: 8px; }
```

### Size vocabulary

Independent of zone, the agent can express the intended size of a component:

```
size="small"    compact, minimal footprint
size="medium"   default, balanced
size="large"    prominent, high information density
```

Size maps to max-width and font scale adjustments in the injected stylesheet. It does not affect grid placement.

### Layer vocabulary

Controls z-axis stacking when multiple components are on screen:

```
layer="base"    fills its zone, part of the main layout flow
layer="float"   sits above base components, does not affect layout
```

```css
[layer="base"]  { z-index: 1; }
[layer="float"] { z-index: 10; pointer-events: auto; }
```

### Full agent positioning example

```html
<div zone="center" size="large" layer="base" class="card elevated animate-in">
  <span class="label-muted">Step 3 of 7</span>
  <p class="text-primary size-lg">Sear the chicken on high heat</p>
  <p class="text-secondary size-sm muted">Don't move it for the first 2 minutes</p>
</div>

<div zone="corner-br" size="small" layer="float" class="card compact glass">
  <span class="timer-display font-mono size-xl">6:00</span>
  <span class="label-muted">Chicken</span>
</div>
```

### Default zone assignments by component type

The agent should follow these defaults unless context requires otherwise. These are documented in the system prompt.

| Component type | Default zone | Default size | Default layer |
|---------------|--------------|--------------|---------------|
| Recipe cards | `center` | `medium` | `base` |
| Step view | `center` | `large` | `base` |
| Timer | `corner-br` | `small` | `float` |
| Suggestion | `bottom` | `medium` | `float` |
| Camera | `center` | `large` | `base` |
| Text response | `center` | `medium` | `base` |
| Alert | `top` | `medium` | `float` |
| Progress bar | `top` | `small` | `base` |

---

## Layer 3 — Behavior (Runtime Registry)

### How it works

All JavaScript behavior is handled by a single runtime script injected into every iframe. The agent never writes JavaScript. It declares interactive intent through `data-component` and `data-*` attributes. The runtime reads these attributes on DOM ready and initializes the corresponding behavior.

The iframe CSP blocks all inline scripts and external script sources except the injected runtime. The agent cannot introduce executable code.

### Runtime initialization

```js
// injected-runtime.js — fully controlled by the app, never generated by the agent

const registry = {
  carousel:   (el) => initCarousel(el),
  timer:      (el) => initTimer(el, el.dataset.duration, el.dataset.autostart),
  camera:     (el) => initCamera(el, el.dataset.prompt),
  tabs:       (el) => initTabs(el),
  accordion:  (el) => initAccordion(el),
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-component]').forEach(el => {
    const init = registry[el.dataset.component]
    if (init) init(el)
    else console.warn(`Unknown component: ${el.dataset.component}`)
  })
})
```

### postMessage protocol

Interactive components communicate with the parent React app via `postMessage`. The runtime never makes network requests directly.

```js
// sent from iframe to parent
window.parent.postMessage({
  type: 'component_event',
  component: 'carousel',
  event: 'slide_changed',
  data: { index: 2 }
}, '*')

window.parent.postMessage({
  type: 'component_event',
  component: 'camera',
  event: 'frames_captured',
  data: { frames: ['<base64>','<base64>','<base64>'] }
}, '*')

window.parent.postMessage({
  type: 'component_event',
  component: 'timer',
  event: 'timer_ended',
  data: { label: 'Chicken' }
}, '*')
```

The parent React app listens for these messages and routes them to the backend via WebSocket.

### Component runtime registry (v1)

| Component name | data-* attributes | Events emitted | Description |
|---------------|-------------------|----------------|-------------|
| `timer` | `data-duration="6m30s"` `data-autostart="true"` `data-label="Chicken"` | `timer_ended` | Countdown timer with optional autostart |
| `carousel` | `data-autoplay="false"` | `slide_changed` | Swipeable slide container, children are slides |
| `camera` | `data-prompt="Is this cooked?"` | `frames_captured`, `capture_error` | Captures 3 frames at 500ms intervals then closes |
| `tabs` | `data-default="0"` | `tab_changed` | Tabbed content switcher |
| `accordion` | none | `item_toggled` | Expandable sections |
| `action-btn` | `data-action="next_step"` | `action_triggered` | Button that fires a named action to the parent |

### Adding a new interactive component

1. Add the behavior function to `injected-runtime.js`
2. Register it in the `registry` object
3. Add a snippet to the design system vector index documenting its HTML structure and `data-*` attributes
4. The agent can use it on the next turn with no prompt changes required

---

## Iframe Sandbox

### CSP header

Every iframe is served with the following Content Security Policy:

```
Content-Security-Policy:
  default-src 'none';
  style-src 'unsafe-inline';
  script-src 'nonce-{random}';
  img-src data: blob:;
  media-src blob:;
  frame-ancestors 'self';
```

Only the injected runtime script carries the nonce. Agent-generated HTML cannot execute scripts under any circumstances.

### Sanitization pipeline

Before the agent's HTML output is written into the iframe, it passes through a sanitizer:

```python
import bleach

ALLOWED_TAGS = [
  'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4',
  'ul', 'ol', 'li', 'img', 'button', 'input'
]

ALLOWED_ATTRIBUTES = {
  '*': ['class', 'zone', 'size', 'layer', 'data-component',
        'data-duration', 'data-autostart', 'data-label',
        'data-prompt', 'data-action', 'data-slide',
        'data-default', 'aria-label', 'role']
}

def sanitize(html: str) -> str:
  return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
```

Any attribute not in the allowlist is stripped. Any tag not in the allowlist is stripped. The sanitizer runs server-side before the HTML is sent to the client.

### Iframe lifecycle

```
1. Agent turn completes, HTML string returned
2. Server sanitizes HTML
3. Sanitized HTML sent to client via WebSocket as { type: "render", html: "..." }
4. React app writes HTML into iframe srcdoc
5. iframe loads injected stylesheet + injected runtime + sanitized HTML
6. Runtime initializes all data-component elements
7. iframe communicates back via postMessage
```

---

## Agent System Prompt Snippet (Rendering Section)

The following is injected into the Main Assistant system prompt on every turn. It is the complete rendering vocabulary the agent needs to know.

```
CANVAS RENDERING

You render UI by returning an HTML string. Follow these rules exactly.

POSITIONING
Every top-level element must have a zone attribute. Use only these zone values:
center, top, bottom, left, right, corner-tl, corner-tr, corner-bl, corner-br

Every top-level element must have a size attribute: small, medium, or large
Every top-level element must have a layer attribute: base or float

Default placements:
- Recipe cards → zone="center" size="medium" layer="base"
- Step view → zone="center" size="large" layer="base"
- Timer → zone="corner-br" size="small" layer="float"
- Suggestion → zone="bottom" size="medium" layer="float"
- Alert → zone="top" size="medium" layer="float"

STYLE
Use only the CSS classes provided in the retrieved snippets below.
Do not invent class names. Do not write inline styles.

INTERACTIVITY
For interactive components, use data-component with the component name.
Available components: timer, carousel, camera, tabs, accordion, action-btn
See snippet documentation for required data-* attributes per component.

Do not write any JavaScript. Do not use onclick or any event attributes.
All behavior is handled automatically by the runtime.

SAFETY
Do not use: script, style, link, iframe, form, input[type=file], or any src attribute pointing to an external URL.

OUTPUT
Return only the HTML string. No explanation, no markdown fences, no preamble.
Multiple components are allowed. Each must have its own zone attribute.
```

---

## Full Render Example

**Context:** User has chosen Pasta Carbonara. Starting step 1. Timer not yet needed.

**Agent output:**

```html
<div zone="center" size="large" layer="base" class="card elevated animate-in">
  <span class="label-muted">Step 1 of 6</span>
  <p class="text-primary size-lg">Bring a large pot of salted water to a boil</p>
  <p class="text-secondary size-sm muted">Use about 1 tbsp of salt per litre of water</p>
</div>

<div zone="top" size="small" layer="base" class="card compact">
  <div class="progress-bar" data-component="progress" data-current="1" data-total="6"></div>
</div>
```

**Context:** User says "how long does this take?" Agent adds a timer.

**Agent output:**

```html
<div zone="center" size="large" layer="base" class="card elevated">
  <span class="label-muted">Step 1 of 6</span>
  <p class="text-primary size-lg">Bring a large pot of salted water to a boil</p>
  <p class="text-secondary size-sm muted">Use about 1 tbsp of salt per litre of water</p>
</div>

<div zone="corner-br" size="small" layer="float" class="card compact glass animate-in"
     data-component="timer" data-duration="10m" data-autostart="true" data-label="Boiling">
  <span class="timer-display font-mono size-xl">10:00</span>
  <span class="label-muted">Boiling</span>
</div>

<div zone="top" size="small" layer="base" class="card compact">
  <div data-component="progress" data-current="1" data-total="6"></div>
</div>
```

**Context:** User says "is this good?" Agent triggers camera.

**Agent output:**

```html
<div zone="center" size="large" layer="base" class="card elevated animate-in"
     data-component="camera" data-prompt="Check if water is boiling vigorously">
  <p class="text-secondary size-sm muted">Let me see...</p>
</div>

<div zone="corner-br" size="small" layer="float" class="card compact glass"
     data-component="timer" data-duration="10m" data-label="Boiling">
  <span class="timer-display font-mono size-xl">8:34</span>
  <span class="label-muted">Boiling</span>
</div>
```

---

## Open Questions

| # | Question | Priority |
|---|----------|----------|
| 1 | Final CSS class naming convention and full class list | High |
| 2 | Visual design of each zone and how they feel at different viewport sizes | High |
| 3 | Animation library for animate-in / animate-out (CSS keyframes vs a small lib) | Medium |
| 4 | How to handle agent output that references a zone already occupied | Medium |
| 5 | Whether `progress` component should be in the runtime registry or pure CSS | Low |
| 6 | Snippet index build pipeline: manual curation vs auto-generated from component library | Low |

---

*This spec governs all rendering decisions in the AI Cooking Assistant. Changes to any layer must be reflected here before implementation begins.*
