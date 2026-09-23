---
name: do-the-shop
description: >-
  Run the weekly grocery shop end to end. Use this whenever the user wants to "do the
  shop", plan the weekly shopping, build a grocery/shopping list from recipes, or work
  out what to buy for the week's dinners, lunches, breakfasts and brunches. Collects recipes for
  each meal, scales them by servings, converts everything to metric, compiles a single
  aisle-grouped shopping list, verifies it with independent checker agents, and deducts
  what the user already has. Prefer this skill for any "what do I need to buy this week"
  style request.
---

# do-the-shop

Orchestrates the whole weekly shop. The guiding principles:

- **Consistency:** every quantity ends up in **metric** (g / ml) or a plain count.
- **Traceability:** every item on the final list says which recipe(s) it's for.
- **Trust but verify:** the ingredient maths and the grouping are checked by fresh,
  no-context agents that *report* problems rather than silently editing, and each check
  loops until it comes back clean.

**Data location:** `data/`
- `recipes/` — saved recipes, both described and URL-derived, each with its own
  ingredients + base servings → `RECIPES_DIR`
- `consumables.md` — replenishables suggestion list → `CONSUMABLES`
- `recipe-urls.md` — browsable index of URL recipes with ratings (not the source of
  ingredient data — that lives in `RECIPES_DIR`) → `URL_LIBRARY`
- `shopping-preferences.md` — standing preferences for the online shop (store, product
  choice, substitutions, dietary/brand/packaging), grown from user feedback → `SHOP_PREFS`

<!-- PAUSED (see note above Step 12): product search is not currently run.
**Product search — free local scraper only (Step 12):** the local scraper
`scripts/ocado_search.py` (stdlib Python; run from a UK IP; no cost) returns real
products with price, unit price, pack size, stock, ratings and `productId`/`sku`/`url`.
It requires a UK IP (Ocado geo-restricts to the UK). If the scraper is unavailable or
can't resolve a given item, that item falls to the browser session (Step 14) to choose.
**No paid product-search service is used** — per user preference, there is no Apify (or
other paid) fallback.
-->

**Scope: Steps 0–11 only.** The skill currently ends at Step 11 (the final, deducted
shopping list). Steps 12–16 (Ocado product matching, browser basket-building, basket
verification, preference capture) are **paused** and commented out below — do not run
them, and do not offer to, until the user re-enables them.

Work through the steps in order. Keep the user's answers organized as you go (a running
scratchpad of recipes → base servings → chosen servings → ingredients is worth keeping).

---

## Step 0 — Ratings sweep
Read `URL_LIBRARY`. If any recipes show `Rating: —`, list them and ask the user to rate
each out of 5. Write the ratings back into the file. This keeps the inspiration library
useful. (If everything is already rated, or the library is empty, skip silently.)

## Step 1 — Collect recipes for each meal (and clarify servings as you go)
Call the **collect-recipes** skill four times, once per meal type, in this order:
1. `weekday dinner`
2. `lunch`
3. `weekday breakfast`
4. `weekend brunch`

Each call returns the chosen recipes for that meal with their `base_servings` and raw
ingredient lists. A meal can legitimately have zero recipes.

**Clarify servings before moving to the next meal.** As soon as a meal's recipes come
back, ask the user how many servings they want for each recipe in *that* meal, and
record the chosen servings next to each recipe (alongside its `base_servings`) in your
scratchpad. Only then move on to the next meal type. This keeps each meal's servings
fresh in the user's mind rather than asking for all of them at the end.

## Step 2 — Consumables
Read `CONSUMABLES` and present the suggestion list, with `default: yes` items pre-ticked.
Ask which to include and whether anything new needs replenishing.

**Important — grow the list:** any new consumable the user names that isn't already in
`CONSUMABLES` gets appended to the appropriate section of that file, so it's suggested
next time. (E.g. user says "toilet roll" and it's missing → add it.) Consumables carry
through to the final list under a **Household / Consumables** group; they aren't scaled.

## Step 3 — Recap servings per recipe
Servings were already captured per meal during Step 1. Before scaling, recap the full
set — every collected recipe with its `base_servings` and chosen servings — so the user
can confirm or adjust in one place. If any recipe still has no chosen servings (e.g. a
meal added out of order), ask for it now.

## Step 4 — Scale each recipe
For every recipe, compute `factor = desired_servings / base_servings` and multiply each
ingredient amount by it. (Described/saved recipes have `base_servings = 1`, so the
factor is just the desired servings.) Example: recipe serves 4, user wants 6 → factor
1.5 → 200 g becomes 300 g. Countable items scale too (2 eggs → 3); round sensibly and
note the rounding rather than hiding it.

**Tinned/canned ingredients don't flatten to a raw weight.** If an ingredient is bought
in tins (tomatoes, beans, sweetcorn, tuna, etc.), express the scaled amount as a whole
number of tins at their known size, e.g. `2 x 400 g tins tomatoes`, not `800 g tomatoes`.
Work out the tin size from how the recipe recorded it (a described recipe's Notes
usually states the tin size it was built from). Compute total weight needed, divide by
tin size, and **round up** to the next whole tin — note any resulting surplus rather
than hiding it (e.g. "3 x 400 g tins needed for 1100 g → 1200 g bought, 100 g surplus").
This carries through unchanged into the compiled list in Step 6.

**Big vegetables normally bought whole don't flatten to a raw weight either.**
Aubergine/eggplant, cauliflower, cabbage, courgette, cucumber, butternut squash, and
similar items should be expressed as a whole-number count, e.g. `2 aubergines`, not
`500 g aubergine` — even if the original recipe gave the ingredient by weight. Convert
using a reasonable typical single-item weight, note the assumption used, round up to
the next whole vegetable, and note any surplus. This carries through unchanged into the
compiled list in Step 6.

**Dry spices and seasonings stay in tsp/tbsp, not grams/ml.** Dry store-cupboard
seasonings — ground spices (cumin, turmeric, cayenne, coriander, cardamom, fenugreek,
amchur, mustard powder, etc.), baking powder, sesame seeds, salt and sugar — are bought
as jars/packets, so their tsp/tbsp amount is a cooking instruction, not a purchase
quantity. Keep them in tsp/tbsp and scale the number (e.g. `1/2 tsp cumin` ×2 →
`1 tsp cumin`); do **not** volume-convert them to ml/g (nobody buys "10 ml turmeric").
By contrast, **liquids** (oils, vinegars, lemon/lime juice, spirits like amaretto) and
**chopped fresh herbs** *are* expressed in ml/g, since those amounts do drive how much
to buy. This mixed convention is intentional — tell the Step 5 checker so it doesn't
flag the spices as unconverted. This carries through into the compiled list in Step 6.

Produce a **per-recipe scaled ingredient list**. Keep them split by recipe at this
stage — do not combine yet.

## Step 5 — Verify the per-recipe maths (loop until clean)
Spawn a fresh **general-purpose agent with no prior context**. Give it: each recipe's
name, base servings, desired servings, the original ingredient list, and your scaled
list. Ask it to check that every ingredient is present and every amount is correctly
scaled and correctly converted to metric, and to **report a list of corrections only —
not to edit anything.**

- If it reports zero issues, continue.
- If it reports issues, apply the fixes yourself, then spawn a *new* fresh agent and
  re-run. Repeat until an agent returns zero issues.
- Cap at 5 rounds; if it still isn't clean, stop and show the user the outstanding
  disagreement rather than looping forever.

See `references/verification.md` for the exact prompt to give the agent.

## Step 6 — Compile the combined list
Merge all scaled per-recipe ingredients (plus the chosen consumables) into **one** list:
- Convert every amount to metric (g / ml) if not already.
- Combine identical ingredients across recipes into a single line, summing amounts in a
  common unit. If two entries truly can't share a unit, keep them as separate lines with
  a note rather than forcing a bad conversion.
- Keep tinned/canned ingredients expressed as whole tins (e.g. `3 x 400 g tins
  tomatoes`), same rule as Step 4. When the same tinned ingredient appears across
  multiple recipes, sum the total weight needed first, then recompute the whole-tin
  count for the combined total (round up, note any surplus) — don't just add tin counts
  from each recipe separately, since that can over-round.
- Same for big whole vegetables (aubergine, cauliflower, cabbage, courgette, cucumber,
  etc.): keep them expressed as a whole-number count (e.g. `4 courgettes`), summing
  total weight/count needed across recipes first, then recomputing the whole-item count
  for the combined total.
- Annotate each line with the recipe(s) it came from, e.g. `500 g onions (Bolognese,
  Frittata)`. Consumables are annotated `(consumable)`.
- **Apply product preferences from `SHOP_PREFS`** (read it fresh). Where a line matches
  a named-product preference, render it with the preferred brand/product in place of the
  generic ingredient (e.g. `eggs` → `Burford Brown medium eggs`), and apply any
  threshold rules (e.g. the granola under/over 360 g rule, which may add a second
  product). These preferences show up on the list itself, not only in the Step 12 brief.
- Group by these aisle categories, in this order:
  **Produce · Meat & Fish · Dairy & Eggs · Bakery · Frozen · Tins & Jars ·
  Dry / Pantry · Herbs & Spices · Drinks · Household / Consumables.**

## Step 7 — Verify the compiled list (loop until clean)
Spawn another fresh **no-context general-purpose agent**. Give it the per-recipe scaled
lists and the compiled grouped list. Ask it to confirm: nothing is missing, no quantity
is wrong, combinations were summed correctly, and every item sits in a sensible group —
**reporting corrections only, not editing.** Loop exactly as in Step 5 (apply fixes,
re-run with a fresh agent, until zero issues, cap 5). Prompt in
`references/verification.md`.

## Step 8 — Present the final list
Show the user the finished, grouped, per-recipe-annotated shopping list.

## Step 9 — Deduct what they already have (interactive checklist)
Capture "what they already have" with an **interactive checklist widget** (the
visualize `show_widget` tool) rather than a free-text question, so the user can mark
items with a tap. Build the widget from the finished pre-deduction list:
- Group items by the same aisle categories, in order, and keep each line's recipe
  annotation.
- Give every item three states: **All** (has the full amount → remove entirely),
  **Some** (has part → reveal an amount field and deduct that amount), and **None**
  (checked, has none → keep in full). "None" is a review aid so the user can confirm
  they've been through every line; include a live "x / N checked" counter.
- A **Send** button collects the state and calls `sendPrompt(...)` to return a
  structured message: a HAVE ALL list (remove entirely) and a HAVE SOME list (each with
  the amount owned). Everything unmarked or marked None stays in full.

The widget renders on desktop but **not on mobile**. If the user is on a phone, fall
back to a plain-markdown `- [ ]` checklist (tappable in the mobile app) or just ask
them to type what they have — don't get stuck trying to make the widget work.

Once the "what I have" answer is back, deduct using **partial deduction**: if they have
300 g of something a recipe needs 500 g of, the list shows the remaining 200 g; only
drop an item entirely when they have enough. Keep the recipe annotations. Watch for
confusable pairs (two sugars, two salts, two oils) — only deduct from the item the user
actually named.

## Step 10 — Verify the deduction (loop until clean)
Spawn one more fresh **no-context agent**. Give it the pre-deduction list, the user's
"already have" list, and the post-deduction list. Ask it to confirm every deduction is
arithmetically correct and nothing was over- or under-deducted — **corrections only.**
Loop until zero issues (same cap-5 rule). Prompt in `references/verification.md`.

## Step 11 — Deliver
Present the final, deducted shopping list. Offer to save it to `data/shopping-lists/`
(dated, e.g. `data/shopping-lists/YYYY-MM-DD.md`) if the user wants a copy.

**STOP here.** This is the end of the skill for now. Do not continue to product
matching, basket-building or anything below.

<!--
PAUSED — Steps 12–16 are deliberately disabled until AI browser interactions are
reliable enough to build the Ocado basket. Kept here intact so they can be re-enabled
by removing this comment block (and the one around "Product search" at the top, plus
the "Scope: Steps 0–11 only" note).

## Step 12 — Match products with the Ocado product scraper
Turn each item on the final list into a real Ocado product. The scraper returns these
fields (name, brand, price, pricePerUnit, packSize, inStock, rating, reviewCount,
productId, sku, url). For **each** item, get candidate products:

> ⛔ **NEVER repeat the burst mistake.** Do the product search as **one warm-session
> batch run** and nothing else. Do **not** loop the single-query command over many items,
> do **not** fire "just one quick test" call before/after the batch, and do **not** run
> two scraper processes at once. Every extra cold request shares your IP and pushes Ocado
> toward the 202-empty soft block, which then costs ~20–30 min of downtime. One batch, one
> warm session, done. This happened once (2026-09-13) and must not happen again.

1. **Local scraper (free) — use BATCH MODE for a whole shop:** don't fire dozens of
   one-off calls. Each single-query call spins up a *fresh cold session* (homepage warm-up
   + API hit), and a rapid burst of those trips Ocado's anti-bot — the search API starts
   returning **HTTP 202 with an empty body** (a soft IP block that then takes ~20–30 min
   of quiet to clear). Instead, write all items to a JSON file and run **one** batch:
   `python3 scripts/ocado_search.py --batch items.json --gap 2` — this warms the session
   **once** and reuses the cookie jar across every query (one request per item, small gap),
   which stays under the radar. `items.json` is a list of
   `{"label","query","sort","limit"}` (sort ∈ price|rating|price-per-unit; use
   price-per-unit for cheapest-per-gram prefs like cashews, rating when reviews matter).
   Output is a JSON object keyed by label → `{query, products:[...]}`. A single query
   still works (`ocado_search.py "<item>" --limit 30 [--sort ...]`) but reserve it for
   one-offs — **never** run a rapid series of them, and don't make stray test calls before
   a batch (they share the IP and can trigger the block). Requires a UK IP; no cost.
2. **Browser session:** if the scraper is unavailable/blocked, or can't resolve a
   particular item, let the browser pick that item's product (Step 14). **No paid fallback
   is used** (per user preference — no Apify or other paid service).

Then, for each item:
- Pick the **preferred product**: honour any named-product preference in `SHOP_PREFS`
  first (Burford Brown eggs, Fitzgerald bagels, the Bio&Me granola 360 g rule,
  cheapest-per-gram cashews, ~1 kg onion bags, etc.); otherwise choose on **best price +
  good reviews** at the right pack size — bigger not smaller when nothing's close — and
  respect stock availability.
- **Store, per item, both the preferred product and the alternatives keyed by their
  Ocado product code/ID** (with name, pack size, price, unit price, rating), so the
  browser session can locate them instantly later.

Produce a **review table**: one row per list item → preferred product, pack size, price
(unit price where it matters), in-stock?, and the recipe annotation.

## Step 13 — Confirm products / swap from alternatives
Show the user the preferred-product table. For any pick they don't want, show the
**stored alternatives for that item** (by code, with price / size / reviews); the user
picks an alternative or drops the item. Update accordingly. The output is the **final
product list with Ocado product codes** — the handover artefact for the browser.

## Step 14 — Hand over to the online shopping session
Brief a fresh Claude session (e.g. Claude in the Chrome extension) that will build the
basket. **Run this session on a cheaper model (Sonnet)** — with the product codes/URLs
already decided, its job is mechanical (navigate → add to basket → confirm), so it
doesn't need Opus; that keeps the token-heavy browser work cheap. Write it as if
briefing someone with **no prior context** — self-contained. The brief contains:
- The **final product list with product codes** from Step 13 (so the session just finds
  each code and adds the quantity — no guessing which product).
- The current contents of `SHOP_PREFS` verbatim (read fresh).
- Standing instructions: add each product by its code at the stated quantity; **report
  anything unavailable / out of stock**; where a coded product is gone, use the next
  stored alternative and flag it; when done, **export the final basket** (HTML if
  possible, else best itemised export) and return it with the unavailable/substitution
  list.

If Step 12 was skipped (scraper not connected), the brief instead carries the plain
final list and asks the session to choose products itself on best price + good reviews,
honouring `SHOP_PREFS`, and to flag unavailable items and better alternatives.

## Step 15 — Verify the basket (loop until clean)
When the shopping session returns its exported basket plus the unavailable/substitution
notes, spawn a fresh **no-context general-purpose agent**. Give it (A) the final product
list (with codes) and (B) the exported basket + unavailable/substitution list. Ask it to
confirm every item is in the basket at the right quantity, or is properly accounted for
as unavailable or substituted — **reporting corrections only, not editing.** Loop as in
Step 5 (apply/relay fixes, fresh agent each round, until zero issues, cap 5). Prompt
style as in `references/verification.md`.

## Step 16 — Capture feedback into preferences
After the shop, ask the user for any feedback — brand preferences, dietary rules,
packaging (loose vs bagged), substitution tolerance, delivery-slot habits, anything.
Append any **new** preferences to `SHOP_PREFS` (de-duplicated, in the right section) so
they carry into every future shop. Same grow-over-time mechanism as the consumables list.

END OF PAUSED STEPS 12–16
-->

---

## Notes on the checker agents
Use a genuinely fresh agent each round (no shared context) — that independence is the
whole point; an agent that helped build the list can't impartially check it. The agents
never edit the list; you apply their corrections so there's a single source of truth.
**Spin the checker agents up on Sonnet** (`model: sonnet`) — the work is arithmetic and
list-matching, well within a cheaper model's range, so there's no need to spend Opus on
it. Reserve Opus for the main planning/decision session.
