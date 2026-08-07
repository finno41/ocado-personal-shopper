# Checker-agent prompts

Each verification step spawns a **fresh general-purpose agent with no prior context**.
Independence is the point: paste in the data it needs, ask for a corrections report,
and never let it edit the list itself. Apply any fixes yourself, then spawn a *brand
new* agent to re-check. Loop until an agent returns zero issues (cap 5 rounds).

Every agent should answer in this shape:

```
STATUS: CLEAN            (or)  STATUS: ISSUES
ISSUES:
- <recipe/item>: <what's wrong> → <suggested correction>
```

`STATUS: CLEAN` with an empty issues list is the exit condition.

---

## Step 5 — per-recipe scaling check

> You are an independent checker. Do NOT edit anything — only report corrections.
>
> For each recipe below you are given: base servings, desired servings, the original
> ingredient list, and a scaled ingredient list someone else produced.
>
> Check that: (1) every original ingredient still appears in the scaled list; (2) each
> amount = original × (desired ÷ base), correct to sensible rounding; (3) every amount
> is expressed in metric (g / ml) or a plain count, with any imperial units correctly
> converted; (4) tinned/canned ingredients are expressed as a whole number of tins at
> their known size (e.g. "3 x 400 g tins"), rounded up from the total weight needed,
> not as a flattened raw weight. Flag anything missing, mis-scaled, mis-converted, or
> given as a raw weight instead of a tin count.
>
> [PASTE: per-recipe data]
>
> Reply using STATUS / ISSUES format.

## Step 7 — compiled-list check

> You are an independent checker. Do NOT edit anything — only report corrections.
>
> You are given (A) the scaled ingredient lists split per recipe, and (B) a single
> compiled shopping list grouped by aisle category.
>
> Check that: (1) nothing from the per-recipe lists is missing from the compiled list;
> (2) ingredients that appear in multiple recipes were summed correctly in a common
> metric unit; (3) no quantity is wrong; (4) each item is in a sensible aisle group;
> (5) every line notes which recipe(s) it came from (consumables marked as such);
> (6) tinned/canned ingredients are expressed as a whole number of tins at their known
> size, with the tin count recomputed from the *combined* total weight across recipes
> (round up, note surplus) rather than tin counts from each recipe just added together.
>
> [PASTE: per-recipe lists + compiled list]
>
> Reply using STATUS / ISSUES format.

## Step 10 — deduction check

> You are an independent checker. Do NOT edit anything — only report corrections.
>
> You are given (A) the shopping list before deduction, (B) the list of items the user
> already has at home, and (C) the list after deducting what they have.
>
> Check that every deduction is arithmetically correct: remaining = needed − owned, in
> a common metric unit; items are only dropped when owned ≥ needed; nothing was
> over-deducted, under-deducted, or deducted from the wrong item. Recipe annotations
> should be preserved.
>
> [PASTE: before list + owned list + after list]
>
> Reply using STATUS / ISSUES format.
