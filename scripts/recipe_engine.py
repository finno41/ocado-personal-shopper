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
