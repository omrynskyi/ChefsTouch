from __future__ import annotations

from typing import Any, Dict, List

# Each case is what you'd pass to graph.ainvoke().
# rubric is used by LLM judges to evaluate output quality.

Case = Dict[str, Any]

DATASET: List[Case] = [
    {
        "intent": "show step 1: bring a large pot of salted water to a boil",
        "context": "Pasta Carbonara, step 1 of 6",
        "canvas_state": {},
        "rubric": "Should show a single step-view card in center zone with the instruction as primary text. Clean, focused, no clutter.",
    },
    {
        "intent": "add a 10 minute timer for boiling the water",
        "context": "Pasta Carbonara, step 1 of 6, water is heating",
        "canvas_state": {
            "step-1": {"id": "step-1", "zone": "center", "html": "<div zone='center'>Step 1</div>"}
        },
        "rubric": "Should add a compact timer in corner-br, floating layer, without disturbing the existing step card.",
    },
    {
        "intent": "show 3 recipe options for pasta",
        "context": "User wants to cook pasta",
        "canvas_state": {},
        "rubric": "Should show multiple recipe cards in center zone. Each card should have a title, description, and tags.",
    },
    {
        "intent": "trigger camera to check if the chicken is cooked through",
        "context": "Chicken thighs, step 4 of 5, searing",
        "canvas_state": {
            "step-4": {"id": "step-4", "zone": "center", "html": "<div zone='center'>Sear chicken</div>"}
        },
        "rubric": "Should add a camera component in center zone. Should include the analysis prompt about checking chicken doneness.",
    },
    {
        "intent": "suggest that the user could chop garlic while waiting",
        "context": "Pasta Carbonara, chicken searing for 6 minutes",
        "canvas_state": {
            "step-3": {"id": "step-3", "zone": "center", "html": "<div zone='center'>Sear chicken</div>"},
            "timer-1": {"id": "timer-1", "zone": "corner-br", "html": "<div zone='corner-br'>6:00</div>"},
        },
        "rubric": "Should add a suggestion card in bottom zone with a proactive parallel task. Should not remove existing components.",
    },
    {
        "intent": "show a warning that the pan is too hot",
        "context": "Pasta Carbonara, step 3",
        "canvas_state": {},
        "rubric": "Should show an alert/warning card in the top zone. Prominent, short warning message.",
    },
    {
        "intent": "show step progress: currently on step 3 of 7",
        "context": "Pasta Carbonara",
        "canvas_state": {},
        "rubric": "Should show a progress indicator in the top zone using data-component=progress with correct data-current and data-total attributes.",
    },
    {
        "intent": "show an ingredients list for creamy pasta carbonara",
        "context": "About to start cooking",
        "canvas_state": {},
        "rubric": "Should show a list of ingredients with quantities in center zone. Items should use text-primary for names and secondary/tag for quantities.",
    },
    {
        "intent": "show step 3 with a 6 minute timer and progress bar at top",
        "context": "Pasta Carbonara, step 3 of 6, searing chicken",
        "canvas_state": {},
        "rubric": "Should produce multiple ops: step card in center, timer in corner-br, progress in top. Each in its correct zone and layer.",
    },
    {
        "intent": "remove the suggestion card, the user dismissed it",
        "context": "Pasta Carbonara, step 3",
        "canvas_state": {
            "suggestion-1": {"id": "suggestion-1", "zone": "bottom", "html": "<div zone='bottom'>Chop garlic</div>"}
        },
        "rubric": "Should emit a single remove op targeting the suggestion component. No add ops.",
    },
]
