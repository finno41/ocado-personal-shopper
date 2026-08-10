# do-the-shop: move mechanical work from agents into code

**Date:** 2026-08-10
**Status:** Approved design — ready for implementation planning

## Problem

The `do-the-shop` skill suite works but has four cost/latency problems:

1. **Combining + conversions are slow.** Scaling, metric conversion, tin/whole-veg
   rounding, cross-recipe combining and aisle grouping are all done by LLM reasoning,
   then re-checked by two fresh checker agents. Slow and token-heavy.
2. **The basket build is slow.** A Claude-in-Chrome agent drives the Ocado UI click by
   click to add each product.
3. **The basket agent substitutes on its own** when a product is unavailable, rather
   than deferring to the user.
4. **The whole thing is expensive on tokens**, the browser agent most of all.

## Goal

Where possible: replace LLM/agent processes with plain, tested code; and do as little as
possible (ideally nothing) in an agent driving the Chrome page. Keep the LLM only for
work that genuinely needs judgment (parsing messy recipe prose, servings/consumables
Q&A, product-quality choices, presentation).

## Division of labour (target)

| Concern | Today | After |
| --- | --- | --- |
| Recipe capture (prose → structured fields) | LLM | LLM (one-time NLP) |
| Scale / convert / round / combine / group | LLM reasoning | `recipe_engine.py` |
| Step 5 & 7 math checker agents | 2 fresh agents | deleted |
| Deduct "what I have" (Steps 9–10) | LLM + checker agent | `deduct.py` |
| Deduction checker agent | fresh agent | deleted (code) |
| Product candidate fetch (Step 12) | `ocado_search.py` | unchanged |
| Preferred-product pick | LLM + user | LLM + user (judgment) |
| Basket build (Step 14) | Chrome LLM agent | `ocado_basket.py` |
| Basket verify (Step 15) | fresh agent | code diff (in `ocado_basket.py`) |

All five checker/doer agents are removed. The Chrome agent is removed entirely.

## New code modules

All are stdlib-only Python in `scripts/`, following the existing `ocado_search.py`
pattern (CLI, JSON in/out, unit tests under `scripts/tests/`).

### 1. `recipe_engine.py`
- **Input:** JSON of per-recipe structured ingredients + each recipe's base servings and
  chosen servings; plus chosen consumables.
- **Does:** per-recipe scaling (`factor = chosen / base`); class-based conversion;
  cross-recipe combining in a common unit; tin and whole-veg rounding on combined
  totals; aisle grouping; recipe annotations; surplus notes.
- **Output:** the compiled, grouped, annotated shopping list as JSON (and a
  markdown renderer for display).
- **Conversion rules keyed by ingredient `class`:**
  - `liquid` (oil, vinegar, cream, juice): tbsp/tsp/cup → ml (1 tbsp = 15 ml,
    1 tsp = 5 ml, 1 cup = 240 ml). Volume→volume, exact.
  - `dry-staple` (flour, sugar, spices, baking powder, sesame): **no conversion** — stays
    in tsp/tbsp; bought as a bag/jar.
  - `by-weight` (chickpeas, tahini): sum grams; imperial → g (1 oz = 28 g, 1 lb = 454 g).
  - `count` (eggs, lemons, garlic): integer counts.
  - `tin` (tinned tomatoes/beans/mango pulp): round the combined weight up to whole tins
    of `tin_size`; note surplus.
  - `whole-veg` (aubergine, cauliflower, cabbage, squash, cucumber, courgette): convert
    to whole-item counts using a typical single-item weight; round up; note surplus.
  - Rare `dry-by-volume-sold-by-weight` (e.g. cups of ground almonds): a small (~10-entry)
    density table (`1 cup ≈ N g`); rough is acceptable because it rounds up to a pack.
- **Replaces:** the slow reasoning in Steps 4/6 **and** the Step 5 & 7 checker agents,
  since correct-by-construction code with unit tests needs no independent LLM check.

### 2. `deduct.py`
- **Input:** compiled list JSON + "what I have" (HAVE ALL / HAVE SOME-with-amounts).
- **Does:** partial deduction (`remaining = needed − owned` in a common unit); drops an
  item only when `owned ≥ needed`; preserves recipe annotations; guards confusable pairs
  by matching on ingredient id, not name.
- **Output:** post-deduction list JSON. Replaces Step 10's checker agent.

### 3. `ocado_basket.py`
- **Input:** final coded product list JSON (code + qty per line) + Ocado session cookies
  from a local file.
- **Does:** for each line, add the product to the trolley by product code at the stated
  quantity via Ocado's trolley API (no browser). **Edit-safe:** reads current trolley
  first; if a code is already present, adds on top (final = existing + requested) and
  reports it. **Flag-only substitutions:** if a code is unavailable for the reserved
  slot, add nothing for it and record it; never auto-swap.
- **Output:** (a) the resulting trolley contents; (b) a report of unavailable items and
  of any pre-existing top-ups; (c) a **code diff** of target vs. resulting trolley
  (replaces the Step 15 verify agent). **Never checks out.**

## Structured recipe format

Recipe files gain a machine-readable ingredients block. Each ingredient:
`{ id, name, qty, unit, class, aisle, tin_size? }`. `class` and `aisle` are set by the
LLM at capture time (`collect-recipes` / `describe-recipe`), which is where messy prose
is normalised. Base servings stay in the file. Existing recipes get a one-time
migration to this format. The human-readable markdown body is retained for reading.

## Safety — session cookies

- `ocado_basket.py` reads cookies from a **local, gitignored file** the user populates
  themselves (e.g. `~/.ocado_session`). Cookies are **never pasted into chat**.
- Cookies are sent **only to ocado.com**.
- The client **builds the trolley and stops** — it never checks out; the user reviews
  and places the order. (Purchases require explicit human action.)
- **Open technical risk / first task:** a small spike to confirm the real add-to-trolley
  request shape — endpoint, method, and whether a CSRF token / specific headers beyond
  cookies are required — before building the client. If unauthenticated-cookie POSTs turn
  out to be infeasible, fall back to the scripted-browser approach (deterministic, no LLM)
  and note it; do not silently revert to an LLM agent.

## Phasing

1. **Phase 1 — `recipe_engine.py`** + structured recipe format + migrate existing
   recipes. Removes pain #1 and the two math checker agents. Self-contained.
2. **Phase 2 — `ocado_basket.py`** (after the spike). Removes pains #2 and #4 and the
   Chrome agent.
3. **Phase 3 — `deduct.py`** + fold basket verification into the code diff. Removes the
   remaining checker agents.

## Skill-doc changes

`do-the-shop/SKILL.md` steps are rewritten to call the scripts instead of describing
LLM reasoning / agent spawns: Step 4–7 → call `recipe_engine.py`; Steps 9–10 → call
`deduct.py`; Steps 14–15 → call `ocado_basket.py`. The "checker agents" notes and the
`references/verification.md` prompts are removed (or trimmed to the one human judgment
step that remains). `collect-recipes` / `describe-recipe` are updated to emit the
structured ingredient fields.

## Testing

Each module ships with `scripts/tests/` unit tests (stdlib `unittest`, as today):
- `recipe_engine`: scaling factors, each conversion class, tin/whole-veg rounding on
  combined totals, combining across recipes, aisle grouping, surplus notes.
- `deduct`: full/partial/none deduction, confusable-pair safety, unit mismatches.
- `ocado_basket`: request construction, edit-safe top-up logic, flag-only OOS handling,
  target-vs-trolley diff. Live API calls are mocked in tests.

## Out of scope (YAGNI)

- Automating the preferred-product *quality* choice (brand/sweetened-vs-pure etc.) —
  stays an LLM + user step.
- Auto-reading cookies from the Chrome profile — local file only for now.
- Any checkout / payment automation — never.
