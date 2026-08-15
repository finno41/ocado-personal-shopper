# Recipe Engine (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the LLM's scale/convert/round/combine/group reasoning (and the two math checker agents) with a deterministic, unit-tested Python engine that turns structured recipe data + chosen servings into the compiled, aisle-grouped shopping list.

**Architecture:** One stdlib-only module, `scripts/recipe_engine.py`, mirroring the existing `scripts/ocado_search.py` pattern (CLI, JSON in/out, `unittest` tests in `scripts/tests/`). Recipes gain a machine-readable ` ```json ` "Ingredients (data)" block; the engine reads that block plus the file's `base_servings`, scales each recipe, converts every amount by ingredient `class`, combines identical ingredients across recipes, rounds tins/whole-veg on combined totals, groups by aisle, and renders JSON + markdown.

**Tech Stack:** Python 3 standard library only (`json`, `re`, `argparse`, `math`, `unittest`). No third-party dependencies.

## Global Constraints

- Standard library only — no pip installs (matches `ocado_search.py`).
- Ingredient `class` is one of exactly: `liquid`, `dry-staple`, `by-weight`, `count`, `tin`, `whole-veg`.
- Aisle is one of exactly, in this order: `Produce`, `Meat & Fish`, `Dairy & Eggs`, `Bakery`, `Frozen`, `Tins & Jars`, `Dry / Pantry`, `Herbs & Spices`, `Drinks`, `Household / Consumables`.
- Conversion constants: `tsp=5 ml`, `tbsp=15 ml`, `cup=240 ml`; `oz=28 g`, `lb=454 g`.
- Dry-staple ingredients are never weight/volume-converted for purchase — summed in ml-equivalent internally, rendered in tbsp, and flagged "bought as pack".
- Tins and whole-veg round **up** to whole units on the **combined** cross-recipe total; surplus is noted, never hidden.
- All displayed numbers are rounded sensibly (integers for counts/tins/whole-veg; ≤1 decimal for g/ml).
- Tests live in `scripts/tests/`, run with `python3 -m unittest discover -s scripts/tests -v`.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

---

## File Structure

- Create `scripts/recipe_engine.py` — the engine: parsing, conversion, scaling, combining, rounding, grouping, rendering, CLI.
- Create `scripts/tests/test_recipe_engine.py` — unit tests for every behavior.
- Modify `data/recipes/README.md` — document the new `## Ingredients (data)` block.
- Modify `data/recipes/example-tomato-pasta.md`, `example-porridge.md`, `example-cheese-sandwich.md` — add data blocks (committed migration examples).
- Modify `.claude/skills/collect-recipes/SKILL.md` and `.claude/skills/describe-recipe/SKILL.md` — instruct emitting the data block.
- Modify `.claude/skills/do-the-shop/SKILL.md` — Steps 4–7 call the engine; remove the two math checker agents.

### Structured ingredient schema (the data block)

Each recipe file gains, after the human-readable `## Ingredients` list:

````markdown
## Ingredients (data)
```json
[
  {"id": "dried-pasta", "name": "dried pasta", "qty": 100, "unit": "g", "class": "by-weight", "aisle": "Dry / Pantry"},
  {"id": "chopped-tomatoes", "name": "tinned chopped tomatoes", "qty": 200, "unit": "g", "class": "tin", "aisle": "Tins & Jars", "tin_size": 400},
  {"id": "garlic", "name": "garlic", "qty": 1, "unit": "clove", "class": "count", "aisle": "Produce"},
  {"id": "basil", "name": "fresh basil", "qty": 5, "unit": "g", "class": "by-weight", "aisle": "Produce"},
  {"id": "olive-oil", "name": "olive oil", "qty": 10, "unit": "ml", "class": "liquid", "aisle": "Dry / Pantry"}
]
```
````

Fields: `id` (kebab-case, the combine key), `name` (display), `qty` (number), `unit` (`g`|`ml`|`tsp`|`tbsp`|`cup`|`oz`|`lb`|`clove`|`count`), `class`, `aisle`, optional `tin_size` (g, required when `class` is `tin`). `qty` of `null` means "to taste" (e.g. salt) — carried through unscaled and rendered without an amount.

---

## Task 1: Recipe file parsing

**Files:**
- Create: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Produces: `parse_recipe(path: str) -> dict` returning `{"name": str, "base_servings": int, "source": str, "ingredients": list[dict]}`. Helper `parse_frontmatter(text: str) -> dict` and `parse_data_block(text: str) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

```python
import os, tempfile, unittest
from scripts import recipe_engine as re_eng

SAMPLE = '''---
name: Example tomato pasta
type: weekday dinner
base_servings: 1
source: described
---

## Ingredients (per 1 serving)
- 100 g dried pasta

## Ingredients (data)
```json
[
  {"id": "dried-pasta", "name": "dried pasta", "qty": 100, "unit": "g", "class": "by-weight", "aisle": "Dry / Pantry"}
]
```

## Notes
whatever
'''

class TestParse(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return path

    def test_parse_recipe_reads_frontmatter_and_data(self):
        path = self._write(SAMPLE)
        r = re_eng.parse_recipe(path)
        self.assertEqual(r["name"], "Example tomato pasta")
        self.assertEqual(r["base_servings"], 1)
        self.assertEqual(r["source"], "described")
        self.assertEqual(len(r["ingredients"]), 1)
        self.assertEqual(r["ingredients"][0]["id"], "dried-pasta")
        self.assertEqual(r["ingredients"][0]["qty"], 100)
```

Note: create `scripts/__init__.py` and `scripts/tests/__init__.py` (empty) so `from scripts import recipe_engine` resolves. Add both in this step.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module 'scripts.recipe_engine' has no attribute 'parse_recipe'`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Deterministic shopping-list engine for do-the-shop. Standard library only."""
import json
import re

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
DATA_BLOCK_RE = re.compile(r"##\s*Ingredients \(data\)\s*\n```json\s*\n(.*?)\n```", re.DOTALL)


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("no frontmatter found")
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.split("#")[0].strip()
    return out


def parse_data_block(text):
    m = DATA_BLOCK_RE.search(text)
    if not m:
        raise ValueError("no '## Ingredients (data)' json block found")
    return json.loads(m.group(1))


def parse_recipe(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = parse_frontmatter(text)
    return {
        "name": fm.get("name", ""),
        "base_servings": int(fm.get("base_servings", "1")),
        "source": fm.get("source", "described"),
        "ingredients": parse_data_block(text),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/__init__.py scripts/tests/__init__.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): parse recipe frontmatter + json data block

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Unit conversion by ingredient class

**Files:**
- Modify: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `to_base(qty, unit, cls, name) -> (float | None, str)` returning the value in the class's base unit and the base-unit label. Base units: `liquid`→`ml`, `by-weight`→`g`, `dry-staple`→`ml` (internal, label `ml-dry`), `count`/`whole-veg`→`count`, `tin`→`g`. `qty=None` returns `(None, <base>)`.
- Module constants `VOLUME_TO_ML`, `WEIGHT_TO_G`, `DENSITY_G_PER_CUP`.

- [ ] **Step 1: Write the failing test**

```python
class TestConvert(unittest.TestCase):
    def test_liquid_tbsp_to_ml(self):
        self.assertEqual(re_eng.to_base(2, "tbsp", "liquid", "olive oil"), (30.0, "ml"))

    def test_by_weight_oz_to_g(self):
        val, unit = re_eng.to_base(1, "oz", "by-weight", "cabbage")
        self.assertAlmostEqual(val, 28.0)
        self.assertEqual(unit, "g")

    def test_by_weight_cup_uses_density(self):
        # 2 cups ground almonds @ 100 g/cup
        val, unit = re_eng.to_base(2, "cup", "by-weight", "ground almonds")
        self.assertEqual((val, unit), (200.0, "g"))

    def test_dry_staple_stays_ml_equiv(self):
        self.assertEqual(re_eng.to_base(1, "tsp", "dry-staple", "cumin"), (5.0, "ml-dry"))

    def test_count_passthrough(self):
        self.assertEqual(re_eng.to_base(3, "clove", "count", "garlic"), (3.0, "count"))

    def test_none_qty(self):
        self.assertEqual(re_eng.to_base(None, "g", "by-weight", "salt"), (None, "g"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `AttributeError: ... 'to_base'`.

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/recipe_engine.py`:

```python
VOLUME_TO_ML = {"ml": 1.0, "tsp": 5.0, "tbsp": 15.0, "cup": 240.0}
WEIGHT_TO_G = {"g": 1.0, "oz": 28.0, "lb": 454.0}
# rough g-per-cup for the rare dry-ingredient-given-by-volume-but-sold-by-weight case
DENSITY_G_PER_CUP = {
    "flour": 120.0, "ground almonds": 100.0, "caster sugar": 200.0,
    "couscous": 180.0, "oats": 90.0, "cocoa": 100.0, "icing sugar": 120.0,
    "breadcrumbs": 108.0, "rice": 185.0, "chopped nuts": 120.0,
}

_BASE_UNIT = {
    "liquid": "ml", "by-weight": "g", "dry-staple": "ml-dry",
    "count": "count", "whole-veg": "count", "tin": "g",
}


def to_base(qty, unit, cls, name):
    base = _BASE_UNIT[cls]
    if qty is None:
        return None, base
    if cls == "liquid":
        return float(qty) * VOLUME_TO_ML[unit], "ml"
    if cls in ("by-weight", "tin"):
        if unit in WEIGHT_TO_G:
            return float(qty) * WEIGHT_TO_G[unit], "g"
        if unit in VOLUME_TO_ML and unit != "ml":  # dry-by-volume via density
            per_cup = DENSITY_G_PER_CUP[name]
            cups = float(qty) * VOLUME_TO_ML[unit] / 240.0
            return cups * per_cup, "g"
        return float(qty), "g"
    if cls == "dry-staple":
        return float(qty) * VOLUME_TO_ML.get(unit, 1.0), "ml-dry"
    # count, whole-veg
    return float(qty), "count"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): class-based unit conversion to base units

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Per-recipe scaling

**Files:**
- Modify: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Produces: `scale_ingredient(ing: dict, factor: float) -> dict` — returns a copy with `qty` multiplied by `factor` (None stays None). Count and whole-veg quantities are **not** rounded here (rounding happens on combined totals in Task 4); the raw scaled float is preserved in a new key `qty_scaled` and original `qty`/`unit`/`class`/`id`/`name`/`aisle`/`tin_size` are retained.

- [ ] **Step 1: Write the failing test**

```python
class TestScale(unittest.TestCase):
    def test_scale_multiplies_qty(self):
        ing = {"id": "x", "name": "x", "qty": 100, "unit": "g", "class": "by-weight", "aisle": "Dry / Pantry"}
        out = re_eng.scale_ingredient(ing, 1.5)
        self.assertEqual(out["qty_scaled"], 150.0)

    def test_scale_none_stays_none(self):
        ing = {"id": "salt", "name": "salt", "qty": None, "unit": "g", "class": "by-weight", "aisle": "Herbs & Spices"}
        out = re_eng.scale_ingredient(ing, 3)
        self.assertIsNone(out["qty_scaled"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `AttributeError: ... 'scale_ingredient'`.

- [ ] **Step 3: Write minimal implementation**

```python
def scale_ingredient(ing, factor):
    out = dict(ing)
    out["qty_scaled"] = None if ing.get("qty") is None else float(ing["qty"]) * float(factor)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): per-recipe ingredient scaling

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Tin and whole-veg rounding

**Files:**
- Modify: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Produces:
  - `round_tins(total_g: float, tin_size: float) -> tuple[int, float]` → `(tins, surplus_g)`, rounding up.
  - `round_whole_veg(total_count: float) -> tuple[int, float]` → `(items, surplus_items)`, rounding up (`total_count` already in whole-item units).
  - Module constant `TYPICAL_WEIGHTS` (g per single item) used later when a whole-veg line is expressed by weight rather than count.

- [ ] **Step 1: Write the failing test**

```python
import math

class TestRounding(unittest.TestCase):
    def test_round_tins_rounds_up_and_reports_surplus(self):
        # 1100 g needed, 400 g tins -> 3 tins (1200 g), 100 g surplus
        self.assertEqual(re_eng.round_tins(1100, 400), (3, 100.0))

    def test_round_tins_exact(self):
        self.assertEqual(re_eng.round_tins(800, 400), (2, 0.0))

    def test_round_whole_veg_rounds_up(self):
        items, surplus = re_eng.round_whole_veg(1.4)
        self.assertEqual(items, 2)
        self.assertAlmostEqual(surplus, 0.6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `AttributeError: ... 'round_tins'`.

- [ ] **Step 3: Write minimal implementation**

```python
import math

TYPICAL_WEIGHTS = {  # grams per single item, for whole-veg given by weight
    "aubergine": 250.0, "cauliflower": 650.0, "cabbage": 900.0,
    "courgette": 200.0, "cucumber": 300.0, "butternut squash": 900.0,
    "onion": 150.0, "red onion": 150.0, "red pepper": 160.0,
}


def round_tins(total_g, tin_size):
    tins = math.ceil(total_g / tin_size)
    return tins, round(tins * tin_size - total_g, 2)


def round_whole_veg(total_count):
    items = math.ceil(total_count)
    return items, round(items - total_count, 2)
```

Note: add `import math` at the top of the module (once) rather than mid-file if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): tin and whole-veg round-up with surplus

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Combine across recipes + consumables

**Files:**
- Modify: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Consumes: `to_base`, `scale_ingredient`, `round_tins`, `round_whole_veg`, `TYPICAL_WEIGHTS`.
- Produces: `combine(recipes: list[dict], consumables: list[dict]) -> list[dict]`.
  Each input recipe dict: `{"name": str, "base_servings": int, "servings": int, "ingredients": list[dict]}`.
  Each output line: `{"id", "name", "aisle", "class", "display": str, "recipes": list[str], "surplus": str|None}` where `display` is the purchase quantity string (e.g. `"274 g"`, `"3 x 400 g tins"`, `"2 whole"`, `"6 tbsp (bought as pack)"`).

- [ ] **Step 1: Write the failing test**

```python
class TestCombine(unittest.TestCase):
    def test_combines_same_ingredient_across_recipes(self):
        r1 = {"name": "A", "base_servings": 1, "servings": 2,
              "ingredients": [{"id": "tahini", "name": "tahini", "qty": 30, "unit": "g", "class": "by-weight", "aisle": "Tins & Jars"}]}
        r2 = {"name": "B", "base_servings": 1, "servings": 3,
              "ingredients": [{"id": "tahini", "name": "tahini", "qty": 20, "unit": "g", "class": "by-weight", "aisle": "Tins & Jars"}]}
        out = re_eng.combine([r1, r2], [])
        line = [x for x in out if x["id"] == "tahini"][0]
        self.assertEqual(line["display"], "120 g")           # 30*2 + 20*3
        self.assertEqual(sorted(line["recipes"]), ["A", "B"])

    def test_tins_summed_then_rounded(self):
        r = {"name": "C", "base_servings": 1, "servings": 3,
             "ingredients": [{"id": "toms", "name": "tinned tomatoes", "qty": 400, "unit": "g", "class": "tin", "aisle": "Tins & Jars", "tin_size": 400}]}
        out = re_eng.combine([r], [])
        line = out[0]
        self.assertEqual(line["display"], "3 x 400 g tins")

    def test_consumables_passthrough(self):
        out = re_eng.combine([], [{"id": "toilet-roll", "name": "toilet roll", "aisle": "Household / Consumables"}])
        self.assertEqual(out[0]["display"], "1")
        self.assertEqual(out[0]["recipes"], ["consumable"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `AttributeError: ... 'combine'`.

- [ ] **Step 3: Write minimal implementation**

```python
def _fmt_num(n):
    return str(int(round(n))) if abs(n - round(n)) < 1e-6 else str(round(n, 1))


def combine(recipes, consumables):
    acc = {}  # id -> aggregate
    for r in recipes:
        factor = r["servings"] / r["base_servings"]
        for ing in r["ingredients"]:
            scaled = scale_ingredient(ing, factor)
            value, base_unit = to_base(scaled["qty_scaled"], ing["unit"], ing["class"], ing["name"])
            slot = acc.setdefault(ing["id"], {
                "id": ing["id"], "name": ing["name"], "aisle": ing["aisle"],
                "class": ing["class"], "tin_size": ing.get("tin_size"),
                "total": 0.0, "base_unit": base_unit, "recipes": set(), "to_taste": False,
            })
            slot["recipes"].add(r["name"])
            if value is None:
                slot["to_taste"] = True
            else:
                slot["total"] += value

    lines = []
    for slot in acc.values():
        lines.append(_render_line(slot))
    for c in consumables:
        lines.append({"id": c["id"], "name": c["name"], "aisle": c["aisle"],
                      "class": "consumable", "display": "1", "recipes": ["consumable"], "surplus": None})
    return lines


def _render_line(slot):
    cls, total = slot["class"], slot["total"]
    surplus = None
    if slot["to_taste"] and total == 0:
        display = "to taste"
    elif cls == "tin":
        tins, surplus_g = round_tins(total, slot["tin_size"])
        display = f"{tins} x {int(slot['tin_size'])} g tins"
        if surplus_g:
            surplus = f"{_fmt_num(surplus_g)} g surplus"
    elif cls == "whole-veg":
        items, surplus_items = round_whole_veg(total)
        display = f"{items} whole"
        if surplus_items:
            surplus = f"{_fmt_num(surplus_items)} item surplus"
    elif cls == "count":
        display = _fmt_num(total)
    elif cls == "dry-staple":
        display = f"{_fmt_num(total / 15.0)} tbsp (bought as pack)"
    elif cls == "liquid":
        display = f"{_fmt_num(total)} ml"
    else:  # by-weight
        display = f"{_fmt_num(total)} g"
    return {"id": slot["id"], "name": slot["name"], "aisle": slot["aisle"],
            "class": cls, "display": display, "recipes": sorted(slot["recipes"]), "surplus": surplus}
```

Note: whole-veg lines given by weight (e.g. `qty` in g) require converting to item count using `TYPICAL_WEIGHTS` inside `to_base`. Extend `to_base`'s `whole-veg` branch: if `unit` in `WEIGHT_TO_G`, return `(qty_in_g / TYPICAL_WEIGHTS[name], "count")`; else passthrough count. Add this now and a test:

```python
    def test_whole_veg_by_weight_uses_typical(self):
        # 500 g courgette @ 200 g each -> 2.5 items
        val, unit = re_eng.to_base(500, "g", "whole-veg", "courgette")
        self.assertEqual((val, unit), (2.5, "count"))
```

Update the `to_base` `count/whole-veg` tail to:

```python
    if cls == "whole-veg" and unit in WEIGHT_TO_G:
        return float(qty) * WEIGHT_TO_G[unit] / TYPICAL_WEIGHTS[name], "count"
    return float(qty), "count"
```

(`TYPICAL_WEIGHTS` is defined in Task 4, which precedes this task.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: PASS (all combine + the whole-veg-by-weight test).

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): combine across recipes with tin/veg/consumable rendering

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Aisle grouping, markdown render, and CLI

**Files:**
- Modify: `scripts/recipe_engine.py`
- Test: `scripts/tests/test_recipe_engine.py`

**Interfaces:**
- Consumes: `parse_recipe`, `combine`.
- Produces:
  - `group_by_aisle(lines: list[dict]) -> list[tuple[str, list[dict]]]` in the fixed aisle order.
  - `render_markdown(grouped) -> str`.
  - `main(argv=None) -> int` CLI: reads a plan JSON from `--plan <file>` or stdin, shape `{"recipes": [{"file": str, "servings": int}], "consumables": [{"id","name","aisle"}]}`; prints compiled JSON to stdout, or markdown when `--markdown` is passed.

- [ ] **Step 1: Write the failing test**

```python
class TestGroupRenderCli(unittest.TestCase):
    def test_group_orders_aisles(self):
        lines = [
            {"id": "a", "name": "amaretto", "aisle": "Drinks", "class": "liquid", "display": "90 ml", "recipes": ["X"], "surplus": None},
            {"id": "b", "name": "onion", "aisle": "Produce", "class": "whole-veg", "display": "2 whole", "recipes": ["X"], "surplus": None},
        ]
        grouped = re_eng.group_by_aisle(lines)
        self.assertEqual([g[0] for g in grouped], ["Produce", "Drinks"])

    def test_render_markdown_includes_annotation(self):
        grouped = [("Produce", [{"name": "onion", "display": "2 whole", "recipes": ["Frittata"], "surplus": None}])]
        md = re_eng.render_markdown(grouped)
        self.assertIn("2 whole onion", md)
        self.assertIn("(Frittata)", md)

    def test_cli_compiles_from_plan(self):
        import io, json as _json, contextlib
        path = self._write(SAMPLE)  # reuse SAMPLE from TestParse-style helper
        plan = {"recipes": [{"file": path, "servings": 2}], "consumables": []}
        pf = self._write(_json.dumps(plan))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = re_eng.main(["--plan", pf])
        self.assertEqual(rc, 0)
        data = _json.loads(buf.getvalue())
        line = [x for x in data if x["id"] == "dried-pasta"][0]
        self.assertEqual(line["display"], "200 g")  # 100 g * 2
```

Add a `_write` helper to this test class (same body as Task 1's).

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest scripts.tests.test_recipe_engine -v`
Expected: FAIL — `AttributeError: ... 'group_by_aisle'` / `'main'`.

- [ ] **Step 3: Write minimal implementation**

```python
import argparse
import sys

AISLE_ORDER = [
    "Produce", "Meat & Fish", "Dairy & Eggs", "Bakery", "Frozen",
    "Tins & Jars", "Dry / Pantry", "Herbs & Spices", "Drinks", "Household / Consumables",
]


def group_by_aisle(lines):
    grouped = []
    for aisle in AISLE_ORDER:
        items = [l for l in lines if l["aisle"] == aisle]
        if items:
            grouped.append((aisle, items))
    return grouped


def render_markdown(grouped):
    out = []
    for aisle, items in grouped:
        out.append(f"## {aisle}")
        for it in items:
            ann = ", ".join(it["recipes"])
            line = f"- {it['display']} {it['name']} ({ann})"
            if it.get("surplus"):
                line += f" — {it['surplus']}"
            out.append(line)
        out.append("")
    return "\n".join(out).strip()


def compile_plan(plan):
    recipes = []
    for entry in plan.get("recipes", []):
        r = parse_recipe(entry["file"])
        r["servings"] = entry["servings"]
        recipes.append(r)
    return combine(recipes, plan.get("consumables", []))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compile a shopping list from structured recipes.")
    ap.add_argument("--plan", help="path to plan JSON; omit to read stdin")
    ap.add_argument("--markdown", action="store_true", help="render markdown instead of JSON")
    args = ap.parse_args(argv)
    raw = open(args.plan, encoding="utf-8").read() if args.plan else sys.stdin.read()
    plan = json.loads(raw)
    lines = compile_plan(plan)
    if args.markdown:
        sys.stdout.write(render_markdown(group_by_aisle(lines)) + "\n")
    else:
        json.dump(lines, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest discover -s scripts/tests -v`
Expected: PASS (all tests across the file).

- [ ] **Step 5: Commit**

```bash
git add scripts/recipe_engine.py scripts/tests/test_recipe_engine.py
git commit -m "feat(recipe-engine): aisle grouping, markdown render, CLI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Migrate example recipes, README, and capture/skill docs

**Files:**
- Modify: `data/recipes/README.md`
- Modify: `data/recipes/example-tomato-pasta.md`, `data/recipes/example-porridge.md`, `data/recipes/example-cheese-sandwich.md`
- Modify: `.claude/skills/collect-recipes/SKILL.md`, `.claude/skills/describe-recipe/SKILL.md`
- Modify: `.claude/skills/do-the-shop/SKILL.md`

**Interfaces:**
- Consumes: the schema and `main` CLI from Tasks 1–6.
- Produces: committed example recipes the engine can parse; skill docs that emit/consume the data block.

- [ ] **Step 1: Add data block to `example-tomato-pasta.md`**

Append after the existing `## Ingredients (per 1 serving)` list:

````markdown
## Ingredients (data)
```json
[
  {"id": "dried-pasta", "name": "dried pasta", "qty": 100, "unit": "g", "class": "by-weight", "aisle": "Dry / Pantry"},
  {"id": "chopped-tomatoes", "name": "tinned chopped tomatoes", "qty": 200, "unit": "g", "class": "tin", "aisle": "Tins & Jars", "tin_size": 400},
  {"id": "garlic", "name": "garlic", "qty": 1, "unit": "clove", "class": "count", "aisle": "Produce"},
  {"id": "basil", "name": "fresh basil", "qty": 5, "unit": "g", "class": "by-weight", "aisle": "Produce"},
  {"id": "olive-oil", "name": "olive oil", "qty": 10, "unit": "ml", "class": "liquid", "aisle": "Dry / Pantry"},
  {"id": "salt", "name": "salt", "qty": null, "unit": "g", "class": "dry-staple", "aisle": "Herbs & Spices"}
]
```
````

- [ ] **Step 2: Add data blocks to the other two example recipes**

Read each file first (`data/recipes/example-porridge.md`, `example-cheese-sandwich.md`), then append an `## Ingredients (data)` block whose entries mirror that file's existing `## Ingredients` prose lines, using the schema fields (`id`, `name`, `qty`, `unit`, `class`, `aisle`, `tin_size` when class is `tin`). Match each prose amount exactly; use `class: dry-staple` for salt/sugar/spices, `liquid` for milk/oil, `by-weight` for cheese/oats/butter, `count` for eggs/bread slices.

- [ ] **Step 3: Verify the engine parses all three examples**

Run:
```bash
python3 -c "import json; from scripts import recipe_engine as e; print(json.dumps(e.compile_plan({'recipes':[{'file':'data/recipes/example-tomato-pasta.md','servings':2},{'file':'data/recipes/example-porridge.md','servings':2},{'file':'data/recipes/example-cheese-sandwich.md','servings':2}],'consumables':[]}), indent=2))"
```
Expected: valid JSON compiled list, no exceptions.

- [ ] **Step 4: Update `data/recipes/README.md`**

Add a section after the existing file-format block documenting the `## Ingredients (data)` JSON block: the field list, the six `class` values, the aisle list, and that `qty: null` = "to taste". State that the human `## Ingredients` list stays for reading and the data block is what the engine consumes.

- [ ] **Step 5: Update capture-skill docs**

In `.claude/skills/collect-recipes/SKILL.md` and `.claude/skills/describe-recipe/SKILL.md`, add an instruction: when saving a recipe, also write the `## Ingredients (data)` JSON block (one object per ingredient with `id`/`name`/`qty`/`unit`/`class`/`aisle`/optional `tin_size`), classifying each ingredient into one of the six classes. Reference `data/recipes/README.md` for the schema.

- [ ] **Step 6: Update `do-the-shop/SKILL.md` Steps 4–7**

Rewrite Steps 4–6 to: build a plan JSON (`recipes` with `file`+`servings`, plus chosen `consumables`) and run `python3 scripts/recipe_engine.py --plan <plan.json> --markdown` to produce the compiled list; the tin/whole-veg/scaling/combining rules now live in the engine, so replace the prose rules with a pointer to it. Delete Step 5 and Step 7 (the two math checker agents) and remove their prompts from `references/verification.md`. Keep Step 8 (present the list).

- [ ] **Step 7: Commit**

```bash
git add data/recipes/README.md data/recipes/example-*.md .claude/skills/collect-recipes/SKILL.md .claude/skills/describe-recipe/SKILL.md .claude/skills/do-the-shop/SKILL.md .claude/skills/do-the-shop/references/verification.md
git commit -m "feat(recipe-engine): migrate examples + wire skills to the engine, drop math checker agents

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** `recipe_engine.py` (Tasks 1–6) covers the spec's Module 1 (scaling, class conversion, tin/whole-veg rounding, combining, grouping, density table). Task 7 covers the structured-recipe-format, migration, capture-skill emission, and removal of Step 5/7 checker agents. Deferred to later plans (as designed): `ocado_basket.py` (Phase 2, needs spike), `deduct.py` + basket verify (Phase 3). Product selection stays LLM+user (out of scope per spec).
- **Placeholder scan:** every code step has runnable code; Task 7 Step 2 references reading real files first because their exact prose isn't in front of us — the schema and class rules to apply are fully specified, so no placeholder logic remains.
- **Type consistency:** `to_base` → `(value, base_unit)` used by `combine`; `scale_ingredient` sets `qty_scaled` consumed by `combine`; `round_tins`/`round_whole_veg` return `(int, float)` used in `_render_line`; `combine` output line shape matches what `group_by_aisle`/`render_markdown`/`main` consume. `TYPICAL_WEIGHTS`/`DENSITY_G_PER_CUP` defined before use.
