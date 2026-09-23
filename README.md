# Ocado personal shopper

A [Claude Code](https://claude.com/claude-code) skill suite that plans your weekly
grocery shop — collects recipes, scales them by servings, converts everything to
metric, builds one aisle-grouped shopping list, verifies the maths with independent
checker agents, and deducts what you already have. The end result is a final shopping
list, ready for you to shop from.

It runs entirely inside Claude Code. You open this repo, say **"do the shop"**, and the
`do-the-shop` skill drives the rest.

> **Status:** the skill currently stops at the final, deducted shopping list. The later
> online-shopping steps (matching items to Ocado products and building the basket in a
> browser) are **paused** — kept in the skill but commented out until AI browser
> automation is reliable enough. See [Paused: Ocado basket-building](#paused-ocado-basket-building).

## Quick start

1. **Clone the repo** and open it in Claude Code (open the folder, then run `claude`).
2. **Seed your working files** from the shipped examples:
   ```bash
   cp data/consumables.example.md          data/consumables.md
   cp data/recipe-urls.example.md          data/recipe-urls.md
   cp data/shopping-preferences.example.md data/shopping-preferences.md
   ```
   (Your `consumables.md`, `recipe-urls.md`, `shopping-preferences.md`, your saved
   recipes, and your shopping lists are all gitignored — they stay private.)
3. **Run it:** in Claude Code, say `do the shop` (or `/do-the-shop`).

The three example recipes under `data/recipes/example-*.md` show the recipe format —
delete them once you've added your own.

## How it works

The `do-the-shop` skill walks these phases (see `.claude/skills/do-the-shop/SKILL.md`):

1. **Rate** any unrated recipes in your URL library, so it stays useful for inspiration.
2. **Collect recipes** per meal — weekday dinner, lunch, weekday breakfast, weekend
   brunch — by pasting a URL, describing a recipe, or picking from your saved recipes.
   URL recipes are fetched for their ingredients and base servings and saved to
   `data/recipes/` so they can be reused. Servings are set per meal as you go.
3. **Consumables** — pick replenishables (toilet roll, washing-up liquid, …) from your
   suggestion list; anything new you name is added to the list for next time.
4. **Scale** each recipe to the servings you want; everything is normalised to metric,
   with tins rounded up to whole tins, big veg to whole items, and dry spices kept in
   tsp/tbsp.
5. **Verify** the per-recipe maths with a fresh, independent checker agent (loops until
   clean).
6. **Compile** one shopping list grouped by aisle, combining shared ingredients and
   applying your product preferences, then **verify** the compiled list with another
   checker.
7. **Deduct** what you already have (an interactive have-all / have-some / none
   checklist), then **verify** the deduction.
8. **Deliver** the final list — optionally saved to `data/shopping-lists/YYYY-MM-DD.md`.

The skill stops there.

Supporting skills: `collect-recipes` (gathers the recipes for one meal) and
`describe-recipe` (captures a recipe from a description, saved normalised to one
serving).

## Paused: Ocado basket-building

These steps are still written into `SKILL.md` (Steps 12–16, inside an HTML comment) but
are not run:

- **Match products** — search Ocado for every list item with the free local scraper
  (`scripts/ocado_search.py`, run once in batch mode), pick the best product on price,
  reviews and your preferences, and let you confirm or swap.
- **Build the basket** — hand the chosen product codes to a browser session that adds
  them to your Ocado basket, then **verify** the basket.
- **Capture feedback** into `shopping-preferences.md`.

To re-enable them, remove the two comment blocks in `SKILL.md` and the
"Scope: Steps 0–11 only" / "STOP here" notes.

The scraper still works on its own — see [`scripts/README.md`](scripts/README.md). It's
free and needs a UK IP. No paid product-search service (e.g. Apify) is used.

## Scripts

- `scripts/ocado_search.py` — free Ocado product search (single query or batch). See
  [`scripts/README.md`](scripts/README.md).
- `scripts/recipe_engine.py` — work in progress: a deterministic, standard-library
  engine for the shopping-list maths (recipe parsing, unit conversion, scaling, tin and
  whole-veg rounding), so it can eventually replace the model doing the arithmetic.
  Plan: `docs/superpowers/plans/2026-08-10-recipe-engine-phase1.md`. Not yet wired into
  the skill.

Run the tests with:
```bash
python3 -m unittest discover -s scripts/tests -t .
```

## Model tips (cost)

- Keep **Opus** for the main planning session (recipe collection, list decisions).
- The **checker agents** run on **Sonnet** — the work is arithmetic and list-matching.

## Data & privacy

Everything personal is gitignored: your saved recipes (`data/recipes/*.md` except the
examples), shopping lists, and your working `consumables.md` / `recipe-urls.md` /
`shopping-preferences.md`, plus `.mcp.json` and `.env`. Only the folder structure,
generic examples, `*.example.md` templates, the skills and the scripts are committed.

## Contributing

All changes go directly on `main` — no feature branches or pull requests.

## Disclaimer

For personal, low-volume use. Scraping Ocado is subject to Ocado's Terms of Service —
use responsibly and at your own risk.
