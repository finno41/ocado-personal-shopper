# Ocado personal shopper

A [Claude Code](https://claude.com/claude-code) skill suite that plans your weekly
grocery shop end to end — collects recipes, scales them by servings, converts everything
to metric, builds one aisle-grouped shopping list, verifies the maths with independent
checker agents, deducts what you already have, and (optionally) matches every item to a
real Ocado product ready to drop into your basket.

It runs entirely inside Claude Code. You open this repo, say **"do the shop"**, and the
`do-the-shop` skill drives the rest.

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

1. **Collect recipes** per meal — weekday dinner, lunch, weekday breakfast, weekend
   brunch — by URL, by description, or from your saved pool. Servings are set per meal.
2. **Scale** each recipe to the servings you want; everything is normalised to metric,
   with tins and whole vegetables handled sensibly.
3. **Verify** the per-recipe maths with a fresh, independent checker agent (loops until
   clean).
4. **Compile** one shopping list grouped by aisle, combining shared ingredients, and
   **verify** the compiled list with another checker.
5. **Deduct** what you already have (an interactive have-all / have-some / none
   checklist), then **verify** the deduction.
6. **(Optional) Match products** on Ocado via the Apify connector — best price + reviews,
   honouring your preferences — and confirm/swap before handing over.
7. **Hand over** to a browser session that adds the chosen products to your basket, then
   **verify** the basket.
8. **Capture feedback** into your `shopping-preferences.md` so it improves each week.

## Optional: automated Ocado product matching (Apify)

Product matching uses the [`studio-amba/ocado-scraper`](https://apify.com/studio-amba/ocado-scraper)
actor via Apify's MCP. To enable it:

1. Create a free [Apify](https://apify.com) account and copy your API token.
2. Copy the connector template and add your token:
   ```bash
   cp .mcp.json.example .mcp.json
   # edit .mcp.json → replace YOUR_APIFY_TOKEN
   ```
3. Restart Claude Code; run `/mcp` to confirm `apify-ocado` is connected.

Notes:
- **UK only:** Ocado geo-restricts its product API to UK IPs, so calls must use a
  **GB residential proxy** (the skill sets this automatically).
- **Cost:** roughly £1–2 per shop (pennies per item). The actor reserves a $5 max-charge
  per run, so your Apify balance must sit above $5 to launch — a payment method clears
  this; the free credit alone won't.
- `.mcp.json` is gitignored — your token never leaves your machine.

If you skip this, the skill falls back to letting the browser session pick products.

## Model tips (cost)

- Keep **Opus** for the planning/decision session (recipe maths, product choice).
- Run the **browser session on Sonnet** — it just navigates and adds to basket.
- The **checker agents** also run fine on Sonnet.

## Data & privacy

Everything personal is gitignored: your saved recipes (`data/recipes/*.md` except the
examples), shopping lists, and your working `consumables.md` / `recipe-urls.md` /
`shopping-preferences.md`, plus `.mcp.json`. Only the folder structure, generic examples,
`*.example.md` templates, and the skills are committed.

## Disclaimer

For personal, low-volume use. Scraping Ocado is subject to Ocado's Terms of Service —
use responsibly and at your own risk.
