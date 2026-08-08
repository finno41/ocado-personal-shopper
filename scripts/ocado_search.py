#!/usr/bin/env python3
"""Search Ocado's product API and print products as JSON.

Requires a UK IP (Ocado geo-restricts its catalogue). Standard library only.
"""

import re

_UNIT_SHORT = {
    "PER_LITRE": "litre",
    "PER_KG": "kg",
    "PER_100_GRAM": "100g",
    "PER_100_ML": "100ml",
    "PER_EACH": "each",
    "PER_75CL": "75cl",
}


def _num(value, default=0.0):
    """Best-effort float from Ocado's string/number amounts."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _slug(name):
    """Turn a product name into the hyphenated slug Ocado uses in product URLs."""
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "product"


def _format_unit_price(unit_price):
    """Ocado unitPrice → e.g. '£0.77/litre'. Amounts in GBX are pence (÷100)."""
    if not isinstance(unit_price, dict):
        return ""
    price = unit_price.get("price") or {}
    amount = _num(price.get("amount"), default=None) if price.get("amount") is not None else None
    if amount is None:
        return ""
    if str(price.get("currency", "")).upper() == "GBX":
        amount = amount / 100.0
    unit = _UNIT_SHORT.get(unit_price.get("unitName", ""),
                           str(unit_price.get("unitName", "")).replace("PER_", "").lower() or "unit")
    return f"£{amount:.2f}/{unit}"


def _build_url(retailer_product_id, name):
    return f"https://www.ocado.com/products/{_slug(name)}/{retailer_product_id}"


def _map_product(it):
    rating_summary = it.get("ratingSummary") or {}
    rating_raw = rating_summary.get("overallRating")
    price = it.get("price") or {}
    retailer_id = str(it.get("retailerProductId", ""))
    return {
        "name": str(it.get("name", "")),
        "brand": str(it.get("brand", "") or ""),
        "price": _num(price.get("amount")),
        "currency": str(price.get("currency", "GBP") or "GBP"),
        "pricePerUnit": _format_unit_price(it.get("unitPrice")),
        "packSize": str(it.get("packSizeDescription", "") or ""),
        "inStock": bool(it.get("available", False)),
        "rating": (None if rating_raw in (None, "") else _num(rating_raw, default=None)),
        "reviewCount": int(_num(rating_summary.get("count"))),
        "productId": retailer_id,
        "sku": str(it.get("productId", "") or ""),
        "url": _build_url(retailer_id, it.get("name", "")),
    }


def parse_products(raw):
    """Flatten Ocado's product-pages/search response into our product schema.

    Aggregates `decoratedProducts` across groups, skips `type: featured`
    (sponsored ads), dedupes by retailer product id, and preserves order.
    """
    groups = raw.get("productGroups", []) if isinstance(raw, dict) else (raw or [])
    seen = set()
    out = []
    for group in groups:
        if group.get("type") == "featured":
            continue
        for it in (group.get("decoratedProducts") or []):
            rid = str(it.get("retailerProductId", ""))
            if not rid or rid in seen:
                continue
            seen.add(rid)
            out.append(_map_product(it))
    return out
