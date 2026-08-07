# Saved recipes

One file per recipe. Two kinds live here side by side, in the same format, so both are
equally pickable from "saved recipes" during a shop:

- **Described recipes**, created by the `describe-recipe` skill. Stored **normalized to
  a single serving** (`base_servings: 1`), so scaling is "multiply every amount by the
  number of servings you want."
- **URL-derived recipes**, saved by the `collect-recipes` skill when a recipe comes in
  via a pasted URL. These keep their **own base serving count** (whatever the source
  states, or the lower end if given as a range) rather than being normalized to 1. Any
  ingredient the user added or changed at collection time (e.g. "also add courgettes")
  is folded directly into the ingredient list, not left as a side-note.

All quantities are metric (g, ml) or a plain count. Non-metric amounts are converted
before saving.

File format (`<slug>.md`):

```
---
name: Tomato & basil pasta
type: weekday dinner        # weekday dinner | lunch | weekday breakfast | weekend brunch
base_servings: 1            # 1 for described recipes; the source's own count for URL recipes
source: described           # described | url
url: <original url>         # only present when source: url
---

## Ingredients (per <base_servings> serving(s))
- 100 g dried pasta
- 150 g tinned chopped tomatoes
- 1 clove garlic
- 5 g fresh basil
- 10 ml olive oil
- salt

## Notes
<optional method notes or reminders>
```
