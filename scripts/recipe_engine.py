"""Deterministic shopping-list engine for do-the-shop. Standard library only."""
import json
import math
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


def scale_ingredient(ing, factor):
    out = dict(ing)
    out["qty_scaled"] = None if ing.get("qty") is None else float(ing["qty"]) * float(factor)
    return out


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
