#!/usr/bin/env python3
"""Search Ocado's product API and print products as JSON.

Requires a UK IP (Ocado geo-restricts its catalogue). Standard library only.
"""

import http.cookiejar
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

# CA bundles to fall back on when Python ships without linked certs
# (common on the python.org macOS build, where the default store is empty).
_CA_BUNDLES = (
    "/etc/ssl/cert.pem",                     # macOS / BSD
    "/etc/ssl/certs/ca-certificates.crt",    # Debian / Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",      # RHEL / Fedora
)

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36")
SEARCH_ENDPOINT = "https://www.ocado.com/api/webproductpagews/v6/product-pages/search"
HOMEPAGE = "https://www.ocado.com/"

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
    review_count = int(_num(rating_summary.get("count")))
    rating_raw = rating_summary.get("overallRating")
    # No reviews → no meaningful rating (avoid a misleading 0.0).
    rating = None if (review_count == 0 or rating_raw in (None, "")) else _num(rating_raw, default=None)
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
        "rating": rating,
        "reviewCount": review_count,
        "productId": retailer_id,
        "sku": str(it.get("productId", "") or ""),
        "url": _build_url(retailer_id, it.get("name", "")),
    }


def build_url(query, limit):
    """Ocado search URL. maxProductsToDecorate caps how many products get full data;
    request a buffer above `limit` to survive sponsored/duplicate filtering."""
    decorate = min(100, max(50, int(limit) + 20))
    params = {
        "includeAdditionalPageInfo": "true",
        "maxPageSize": "300",
        "maxProductsToDecorate": str(decorate),
        "q": query,
        "tag": "web",
    }
    return SEARCH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def _ssl_context():
    """Verified TLS context; loads a system CA bundle if Python's store is empty."""
    ctx = ssl.create_default_context()
    if not ctx.get_ca_certs():
        for bundle in _CA_BUNDLES:
            if os.path.exists(bundle):
                ctx.load_verify_locations(bundle)
                break
    return ctx


def _opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPSHandler(context=_ssl_context()),
    )


def warm_opener(timeout=20):
    """Build an opener and warm a cookie session on the homepage.

    Returns an opener carrying global_sid/AWSALB/VISITORID cookies. Reuse it across many
    searches so we present one persistent, human-looking session rather than a fresh cold
    connection per query (which trips Ocado's anti-bot). Requires a UK IP.
    """
    opener = _opener()
    base = {"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en-US;q=0.9"}
    opener.open(urllib.request.Request(HOMEPAGE, headers=base), timeout=timeout).read()
    return opener


def fetch_search(query, limit=30, timeout=20, opener=None):
    """Call the search API and return the raw parsed JSON.

    If `opener` is given, reuse that already-warmed session (batch mode). Otherwise build
    and warm a one-shot session for this single call. Requires a UK IP. Raises urllib
    errors on failure.
    """
    base = {"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en-US;q=0.9"}
    if opener is None:
        opener = warm_opener(timeout=timeout)
    api_headers = dict(base)
    api_headers.update({
        "Accept": "application/json; charset=utf-8",
        "ecom-request-source": "web",
        "Referer": "https://www.ocado.com/search?q=" + urllib.parse.quote(query),
    })
    req = urllib.request.Request(build_url(query, limit), headers=api_headers)
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_batch(items, gap=2.0, timeout=20):
    """Run many searches through ONE warmed session, reusing the cookie jar.

    `items` is a list of dicts: {label?, query, sort?, limit?}. Returns a dict keyed by
    label (falling back to query) -> {query, products: [...]} or {query, error}. A small
    `gap` spaces requests; a failed query re-warms the session and retries a couple times.
    """
    import time
    opener = warm_opener(timeout=timeout)
    results = {}
    for idx, item in enumerate(items):
        query = item["query"]
        label = item.get("label") or query
        sort = item.get("sort")
        limit = int(item.get("limit", 30))
        if idx:
            time.sleep(gap)
        products = None
        for attempt in range(3):
            try:
                products = parse_products(fetch_search(query, limit, timeout=timeout, opener=opener))
                break
            except Exception:  # noqa: BLE001 - blocked/non-JSON; back off, re-warm, retry
                time.sleep(gap * (attempt + 2))
                try:
                    opener = warm_opener(timeout=timeout)
                except Exception:
                    pass
        if products is None:
            results[label] = {"query": query, "error": "fetch failed after retries", "products": []}
        else:
            results[label] = {"query": query, "products": sort_products(products, sort)[:limit]}
    return results


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


def _unit_price_value(product):
    """Numeric £/unit from a product's pricePerUnit string, for sorting. inf if absent."""
    m = re.search(r"£\s*([0-9]+(?:\.[0-9]+)?)", product.get("pricePerUnit", "") or "")
    return float(m.group(1)) if m else float("inf")


def sort_products(products, sort):
    """Return products ordered by the chosen key (client-side). Unknown/None = as-is."""
    if sort == "price":
        return sorted(products, key=lambda p: p["price"])
    if sort == "rating":
        return sorted(products, key=lambda p: (p["rating"] is None, -(p["rating"] or 0)))
    if sort == "price-per-unit":
        return sorted(products, key=_unit_price_value)
    return products


def main(argv=None):
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Search Ocado and print products as JSON.")
    ap.add_argument("query", nargs="?", help="search keyword, e.g. milk")
    ap.add_argument("--limit", type=int, default=30, help="max products (default 30)")
    ap.add_argument("--sort", choices=["price", "rating", "price-per-unit"], default=None,
                    help="order results before output (client-side)")
    ap.add_argument("--batch", metavar="FILE",
                    help="path to a JSON file with a list of {label?,query,sort?,limit?}; "
                         "runs all queries through one warmed session and prints a JSON "
                         "object keyed by label. '-' reads the JSON from stdin.")
    ap.add_argument("--gap", type=float, default=2.0,
                    help="seconds between batch queries (default 2.0)")
    args = ap.parse_args(argv)

    if args.batch:
        try:
            if args.batch == "-":
                items = json.load(sys.stdin)
            else:
                with open(args.batch, encoding="utf-8") as fh:
                    items = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            print(f"ocado_search: could not read batch file: {exc}", file=sys.stderr)
            return 1
        results = run_batch(items, gap=args.gap)
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    if not args.query:
        ap.error("a query is required unless --batch is given")

    try:
        products = parse_products(fetch_search(args.query, args.limit))
    except Exception as exc:  # noqa: BLE001 - fail cleanly so the caller can fall back
        print(f"ocado_search: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if not products:
        print("ocado_search: no products returned (blocked, or non-UK IP?)", file=sys.stderr)
        return 2

    products = sort_products(products, args.sort)[:args.limit]
    json.dump(products, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
