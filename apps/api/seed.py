"""
Seed script: inserts 5 sample recipes with real nomic-embed-text-v1 embeddings.

Prerequisites:
  1. Run supabase/resize_embedding_768.sql in the Supabase SQL Editor to resize
     the embedding column from vector(1536) to vector(768).
  2. Start LM Studio and load the nomic-embed-text-v1 model.

Usage:
    cd apps/api && python seed.py
"""

import asyncio
import sys

from db import get_client
from llm import get_embed_model

EMBEDDING_DIM = 768  # nomic-embed-text-v1 output dimension


RECIPES = [
    {
        "title": "Spaghetti Aglio e Olio",
        "description": "A classic Roman pasta with golden garlic, chili flakes, and good olive oil. Done in 20 minutes.",
        "duration_minutes": 20,
        "servings": 2,
        "tags": ["pasta", "quick", "vegetarian", "italian"],
        "steps": [
            {"step_number": 1, "instruction": "Bring a large pot of salted water to a boil.", "tip": "It should taste like the sea."},
            {"step_number": 2, "instruction": "Cook 200g spaghetti until al dente per package directions."},
            {"step_number": 3, "instruction": "While pasta cooks, slice 6 garlic cloves thin. Warm 4 tbsp olive oil in a large pan over medium-low heat."},
            {"step_number": 4, "instruction": "Add garlic and ½ tsp chili flakes to the oil. Cook 3 minutes until garlic is golden — not brown.", "tip": "Pull it early; it keeps cooking off heat."},
            {"step_number": 5, "instruction": "Reserve 1 cup pasta water, then drain pasta. Add pasta to the pan with ¼ cup pasta water. Toss vigorously 2 minutes."},
            {"step_number": 6, "instruction": "Taste, adjust salt, add parsley, and serve immediately."},
        ],
    },
    {
        "title": "Crispy Sheet-Pan Chicken Thighs",
        "description": "Bone-in thighs roasted at high heat with garlic and lemon. Foolproof crispy skin every time.",
        "duration_minutes": 45,
        "servings": 4,
        "tags": ["chicken", "roasted", "gluten-free", "high-protein"],
        "steps": [
            {"step_number": 1, "instruction": "Preheat oven to 220°C (425°F). Pat 4 bone-in, skin-on chicken thighs very dry with paper towels.", "tip": "Dry skin = crispy skin."},
            {"step_number": 2, "instruction": "Season all over with 1 tsp salt, ½ tsp black pepper, ½ tsp paprika, and a drizzle of olive oil."},
            {"step_number": 3, "instruction": "Place skin-side up on a rimmed baking sheet with 4 smashed garlic cloves and lemon slices."},
            {"step_number": 4, "instruction": "Roast 35-40 minutes until skin is deep golden and internal temp reaches 74°C (165°F)."},
            {"step_number": 5, "instruction": "Rest 5 minutes before serving.", "tip": "The resting makes the juices redistribute."},
        ],
    },
    {
        "title": "Classic French Omelette",
        "description": "Silky, pale yellow, barely set inside. The French technique that separates cooks from chefs.",
        "duration_minutes": 10,
        "servings": 1,
        "tags": ["eggs", "quick", "vegetarian", "french", "breakfast"],
        "steps": [
            {"step_number": 1, "instruction": "Crack 3 cold eggs into a bowl. Season with salt and a tiny pinch of white pepper. Beat with a fork until just combined — no air bubbles."},
            {"step_number": 2, "instruction": "Heat a small nonstick pan over medium-high. Add 1 tbsp butter and let it melt and foam."},
            {"step_number": 3, "instruction": "Pour in eggs. Immediately shake the pan and stir with a fork in small circles while moving the pan.", "tip": "Never stop moving — you're building a creamy curd."},
            {"step_number": 4, "instruction": "When eggs are just barely set (still slightly wet on top), stop stirring. Tilt the pan away from you and roll the omelette onto a plate."},
            {"step_number": 5, "instruction": "It should be pale yellow with no browning. Serve immediately."},
        ],
    },
    {
        "title": "One-Pot Lentil Soup",
        "description": "Hearty red lentil soup with cumin, turmeric, and a lemon finish. Pantry staple, zero fuss.",
        "duration_minutes": 35,
        "servings": 4,
        "tags": ["soup", "vegetarian", "vegan", "legumes", "budget"],
        "steps": [
            {"step_number": 1, "instruction": "Dice 1 onion, 2 garlic cloves, and 1 carrot. Warm 2 tbsp olive oil in a large pot over medium heat."},
            {"step_number": 2, "instruction": "Cook onion and carrot 5 minutes until soft. Add garlic, 1 tsp cumin, ½ tsp turmeric, and ¼ tsp cayenne. Cook 1 minute."},
            {"step_number": 3, "instruction": "Add 300g rinsed red lentils, 1.2L vegetable stock, and 400g canned tomatoes. Bring to a boil."},
            {"step_number": 4, "instruction": "Reduce heat and simmer 20 minutes, stirring occasionally, until lentils are completely soft.", "tip": "Red lentils dissolve — that's what you want."},
            {"step_number": 5, "instruction": "Use an immersion blender to partially blend the soup for a creamy-chunky texture. Season with salt and a big squeeze of lemon."},
        ],
    },
    {
        "title": "Pan-Seared Salmon with Herb Butter",
        "description": "Restaurant-quality salmon in 12 minutes. Crispy skin, basted with garlic herb butter.",
        "duration_minutes": 15,
        "servings": 2,
        "tags": ["fish", "salmon", "quick", "gluten-free", "high-protein"],
        "steps": [
            {"step_number": 1, "instruction": "Take 2 salmon fillets (skin-on) out of the fridge 15 minutes before cooking. Pat dry, season with salt and pepper."},
            {"step_number": 2, "instruction": "Heat a stainless or cast iron pan over medium-high until very hot. Add 1 tbsp neutral oil."},
            {"step_number": 3, "instruction": "Place salmon skin-side down. Press gently with a spatula for 10 seconds so skin makes full contact. Cook 4 minutes without touching.", "tip": "You'll see the color change creeping up the sides — that's your guide."},
            {"step_number": 4, "instruction": "Flip. Add 2 tbsp butter, 2 smashed garlic cloves, and a thyme sprig to the pan. Tilt pan and baste continuously for 2 minutes."},
            {"step_number": 5, "instruction": "Remove when center is just barely opaque. Rest 1 minute and serve with lemon."},
        ],
    },
]


async def main() -> None:
    client = get_client()

    existing = client.table("recipes").select("recipe_id").execute()
    if existing.data:
        print(f"Found {len(existing.data)} existing recipes — skipping seed.")
        sys.exit(0)

    print("Embedding recipes with nomic-embed-text-v1 via LM Studio…")
    embed_model = get_embed_model()
    texts = [f"{r['title']}. {r['description']}" for r in RECIPES]
    embeddings = await embed_model.aembed_documents(texts)  # single batched call

    rows = []
    for recipe, embedding in zip(RECIPES, embeddings):
        row = {**recipe, "steps": list(recipe["steps"]), "embedding": embedding}
        rows.append(row)

    result = client.table("recipes").insert(rows).execute()
    print(f"Seeded {len(result.data)} recipes.")


if __name__ == "__main__":
    asyncio.run(main())
