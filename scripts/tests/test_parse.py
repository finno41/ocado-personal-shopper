import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ocado_search import parse_products  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ocado_search_sample.json")
REQUIRED = {"name", "brand", "price", "currency", "pricePerUnit", "packSize",
            "inStock", "rating", "reviewCount", "productId", "sku", "url"}


def _raw():
    return json.load(open(FIXTURE))


def test_parse_returns_products_with_full_schema():
    products = parse_products(_raw())
    assert isinstance(products, list) and len(products) >= 1
    for p in products:
        assert REQUIRED <= set(p.keys())
        assert isinstance(p["price"], (int, float))
        assert isinstance(p["inStock"], bool)
        assert isinstance(p["reviewCount"], int)
        assert p["rating"] is None or isinstance(p["rating"], (int, float))
        assert isinstance(p["name"], str) and p["name"]
        assert isinstance(p["productId"], str) and p["productId"]


def test_sponsored_only_products_are_skipped():
    raw = _raw()

    def ids_in(pred):
        return {
            str(p.get("retailerProductId"))
            for g in raw["productGroups"] if pred(g.get("type"))
            for p in (g.get("decoratedProducts") or [])
        }

    featured_only = ids_in(lambda t: t == "featured") - ids_in(lambda t: t != "featured")
    organic_ids = ids_in(lambda t: t != "featured")
    out_ids = {p["productId"] for p in parse_products(raw)}
    # products that appear ONLY as sponsored ads must be excluded ...
    assert featured_only.isdisjoint(out_ids)
    # ... and every product returned came from an organic (non-featured) group
    assert out_ids <= organic_ids


def test_no_duplicate_products():
    ids = [p["productId"] for p in parse_products(_raw())]
    assert len(ids) == len(set(ids))


def test_values_are_well_formed():
    p = parse_products(_raw())[0]
    assert p["currency"] == "GBP"
    assert p["url"].startswith("https://www.ocado.com/products/")
    assert p["url"].rstrip("/").endswith(p["productId"])


if __name__ == "__main__":
    # Stdlib-only runner (no pytest dependency): run every test_* function.
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
