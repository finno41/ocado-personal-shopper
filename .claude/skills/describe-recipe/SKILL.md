---
name: describe-recipe
description: >-
  Capture a single recipe by description (not a URL) and save it for reuse. Use this
  whenever the user wants to add a recipe by describing it, or when collect-recipes /
  do-the-shop routes the "describe" path here. Before asking the user to describe
  anything, always offer their existing saved recipes so they can reuse one instead of
  re-describing it. Recipes are saved normalized to ONE serving so they scale cleanly.
---

# describe-recipe

Turn a spoken/typed recipe description into a saved, reusable recipe. Everything is
stored **per single serving** and **in metric**, because that makes later scaling
("I want 6 servings") a trivial multiplication and keeps the whole shop consistent.

**Data location:** `data/recipes/`
(referred to below as `RECIPES_DIR`).

## Flow

### 1. Offer existing saved recipes first
Before asking the user to describe anything, read the files in `RECIPES_DIR` and show
what's already saved, filtered to the relevant meal type if one was passed in. Present
them as a short numbered list (name — one-line note). Ask:

> Want to reuse one of these, or describe a new recipe?

If they pick an existing one, load that file and return it. Done — no need to ask them
to describe anything.

### 2. Describe path
If they want a new recipe, ask for **the ingredients of a single serving**. Phrase it
plainly, e.g.:

> Describe the recipe — just give me the ingredients for **one** serving (amounts +
> item). If it's easier to tell me amounts for several servings, say how many and I'll
> divide down.

Capture: recipe name, meal type (weekday dinner / lunch / weekday breakfast / weekend
brunch), and the per-serving ingredient list.

### 3. Normalize
- If the user gave amounts for N servings, divide every amount by N to get one serving.
- Convert **every** amount to metric (g / ml), even a lone imperial item. Use standard
  conversions (1 cup water ≈ 240 ml, 1 tbsp ≈ 15 ml, 1 tsp ≈ 5 ml, 1 oz ≈ 28 g,
  1 lb ≈ 454 g, 1 stick butter ≈ 113 g). For countable items (eggs, cloves, onions)
  keep the count.
  **Exception — dry spices/seasonings stay in tsp/tbsp:** ground spices, baking powder,
  sesame seeds, salt and sugar are bought as jars/packets, so keep their tsp/tbsp amount
  rather than converting to ml/g. Liquids (oils, vinegars, juices, spirits) and chopped
  fresh herbs still convert to ml/g. See do-the-shop Step 4.
- If an amount is genuinely vague ("a splash", "to taste"), keep it as-is rather than
  inventing precision.
- If the user just says "cheese" with no type specified, record it as **cheddar
  cheese** — that's the household default.

### 4. Save
Write `RECIPES_DIR/<slug>.md` using the format documented in `RECIPES_DIR/README.md`
(frontmatter with `name`, `type`, `base_servings: 1`, `source: described`, then a
`## Ingredients (per 1 serving)` list, optional `## Notes`). Slug = lowercase kebab of
the name.

If a file with that slug already exists, ask whether to overwrite or save under a new
name.

### 5. Return
Report back the saved recipe's name, type, and per-serving ingredients so the caller
(collect-recipes / do-the-shop) can carry on. Return the base servings as **1**.
