---
name: collect-recipes
description: >-
  Collect the recipes for one meal type (weekday dinner, lunch, weekday breakfast, or
  weekend brunch) during a shop. Use this when do-the-shop needs recipes for a meal, or when the user
  wants to gather recipes for a specific meal slot. Offers three paths per meal: paste
  URL(s), describe a recipe, or pick from saved recipes. Fetches URL recipes for their
  ingredients + base servings and logs them to the recipe library. Returns a clean,
  structured list of chosen recipes with per-recipe ingredient lists.
---

# collect-recipes

Gather the recipes for **one meal type** and return them in a consistent structure so
`do-the-shop` can scale and combine them later. Call this once per meal slot.

**Argument:** the meal type — one of `weekday dinner`, `lunch`, `weekday breakfast`,
`weekend brunch`. Each meal type draws from its own separate pool of saved recipes
(filtered by the recipe file's `type` field).

**Data location:** `data/`
- `recipes/` — saved recipes, both described and URL-derived, each with its own
  ingredients + base servings → `RECIPES_DIR`
- `recipe-urls.md` — browsable index of URL recipes with ratings (for inspiration and
  the ratings sweep, not the source of ingredient data) → `URL_LIBRARY`

## Flow

### 1. Ask
Ask whether there are any recipes for this meal type, e.g. for `weekday dinner`:

> Any **weekday dinner** recipes this week? You can:
> 1. Paste one or more URLs
> 2. Describe a recipe
> 3. Pick from your saved recipes

The user may give several recipes, mix paths, or say none. Keep going until they're
done with this meal.

### 2a. URL path
For each URL, fetch the page (WebFetch) and extract: recipe name, the full ingredient
list, the base serving count ("Serves N"), and a one-line description.

- If a fetch fails or is blocked, ask the user to paste the ingredients + serving count
  for that recipe instead. Don't guess.
- If the serving count is given as a range (e.g. "Serves 2-3" or "Serves 2-4"), use the
  **lower end** as the base serving count. Don't ask the user each time — this is a
  standing rule.
- If the user adds or changes an ingredient for this recipe (e.g. "also add
  courgettes"), **fold it directly into the ingredient list** as if it were always part
  of the recipe — don't leave it as a side-note to be reapplied at scaling time later.
- Convert every ingredient amount to metric (g / ml), same conversions as
  describe-recipe (1 lb ≈ 454 g, 1 oz ≈ 28 g, 1 cup ≈ 240 ml, 1 tbsp ≈ 15 ml,
  1 tsp ≈ 5 ml). Keep counts for countable items. Vague amounts ("a splash", "to taste")
  stay as-is. If an ingredient just says "cheese" with no type specified, record it as
  **cheddar cheese** — that's the household default.
- **Save the recipe** to `RECIPES_DIR/<slug>.md`, same file format as described recipes
  (see `RECIPES_DIR/README.md`), plus two extra frontmatter fields: `source: url` and
  `url: <the url>`. `base_servings` is whatever was extracted (not forced to 1 — URL
  recipes keep their own serving count). If a file with that slug already exists, ask
  whether to overwrite or save under a new name.
- Also log the recipe to `URL_LIBRARY` for browsing/ratings (name, URL, type, serves,
  description, `Rating: —`), newest at top — unless the same URL is already there. New
  URL recipes are always saved **unrated**; do-the-shop will collect the rating on the
  next shop. `URL_LIBRARY` is just an index for browsing and ratings — the ingredients
  live in the `RECIPES_DIR` file, not here.

### 2b. Describe path
Invoke the **describe-recipe** skill (pass along this meal type so it can filter the
saved list). It handles offering existing recipes, capturing a one-serving description,
converting to metric, and saving. Take its returned recipe.

### 2c. Saved-recipes path
Show the user their saved recipes for this meal type from `RECIPES_DIR` — this now
includes both described and URL-derived recipes — as a numbered list. Load whichever
they pick.

### 3. Return
Return a structured list for this meal type. For each chosen recipe include:
- `name`
- `source` (described / url — where the recipe's ingredients originally came from)
- `base_servings` (the recipe's own serving count, from its saved file)
- `ingredients` — the ingredient list as stored in the file (already metric; do NOT
  scale here — do-the-shop handles scaling once it knows the desired servings)
