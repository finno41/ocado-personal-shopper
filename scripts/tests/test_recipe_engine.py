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
