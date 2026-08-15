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
