# Ocado Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a free, self-hosted Python CLI (`scripts/ocado_search.py`) that queries Ocado's product-search API from a UK IP and prints products as JSON matching the fields the do-the-shop skill consumes.

**Architecture:** Stdlib-only Python 3. Three pure-ish units — `fetch_search` (HTTP + session), `parse_products` (raw JSON → output schema), `main` (argparse → fetch → parse → stdout). Reverse-engineered from a captured request. Skill Step 12 gains a preference order: local script → Apify → browser.

**Tech Stack:** Python 3 standard library (`urllib`, `json`, `argparse`); `pytest` (or stdlib `unittest`) for the parser test.

## Global Constraints

- **Stdlib-only** for the script — no third-party imports (`requests` etc. are banned).
- **No committed secrets:** never commit session cookies, tokens, or personal data (e.g. delivery postcode). The fixture must be scrubbed; the script acquires any session at runtime.
- **Output schema (verbatim):** each product object has keys `name` (str), `brand` (str), `price` (number), `currency` (str), `pricePerUnit` (str), `packSize` (str), `inStock` (bool), `rating` (number|null), `reviewCount` (number), `productId` (str), `sku` (str), `url` (str). Missing values are `null`/`""`, never omitted.
- **Default `--limit` is 30** (local scraper is free). The Apify fallback stays ~10.
- Repo root: `/Users/oliverfinn/Dropbox/Documents/Shop Data` (the `ocado-personal-shopper` repo).

---

### Task 1: Capture the Ocado search request and save a scrubbed fixture

**Files:**
- Create: `scripts/tests/fixtures/ocado_search_sample.json`
- Create: `scripts/tests/fixtures/CAPTURE_NOTES.md` (endpoint + params; **no secrets**)

- [ ] **Step 1: User captures the request.** In Chrome on ocado.com: dev tools → Network → search a term (e.g. "milk") → click the request that returns product JSON → right-click → Copy → "Copy as cURL". Paste it into the chat.

- [ ] **Step 2: Extract the shape.** From the cURL, record in `CAPTURE_NOTES.md`: the endpoint URL, the query parameters (which one is the search term, which is the page-size/limit, which is sort), the HTTP method, and which headers/cookies are required. **Note whether a session cookie or delivery postcode is needed, but do NOT paste the cookie value into the file.**

- [ ] **Step 3: Save a scrubbed response fixture.** Save the JSON *response body* to `scripts/tests/fixtures/ocado_search_sample.json`. Remove anything session/personal (auth tokens, basket, account, postcode). Keep the product list intact.

- [ ] **Step 4: Verify the fixture is valid JSON and holds products**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
python3 -c "import json;d=json.load(open('scripts/tests/fixtures/ocado_search_sample.json'));print(type(d)); print('looks non-empty:', bool(d))"
```
Expected: prints a type and `looks non-empty: True`.

- [ ] **Step 5: Commit**
```bash
git add scripts/tests/fixtures/
git commit -m "Add captured Ocado search fixture and notes (scrubbed)"
```

---

### Task 2: `parse_products` — map the API response to the output schema (TDD)

**Files:**
- Create: `scripts/ocado_search.py` (this task adds `parse_products` only)
- Create: `scripts/tests/test_parse.py`

**Interfaces:**
- Produces: `parse_products(raw: dict | list) -> list[dict]` — each dict matches the Global-Constraints output schema.

- [ ] **Step 1: Write the failing test** (schema is known; fixture-specific value asserts added after inspecting the fixture)
```python
# scripts/tests/test_parse.py
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ocado_search import parse_products

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ocado_search_sample.json")
REQUIRED = {"name","brand","price","currency","pricePerUnit","packSize",
            "inStock","rating","reviewCount","productId","sku","url"}

def test_parse_returns_products_with_full_schema():
    raw = json.load(open(FIXTURE))
    products = parse_products(raw)
    assert isinstance(products, list) and len(products) >= 1
    for p in products:
        assert REQUIRED <= set(p.keys())           # every required key present
        assert isinstance(p["price"], (int, float))
        assert isinstance(p["inStock"], bool)
        assert isinstance(p["name"], str) and p["name"]
        assert isinstance(p["productId"], str) and p["productId"]
```

- [ ] **Step 2: Run it and watch it fail**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data/scripts"
python3 -m pytest tests/test_parse.py -q
```
Expected: FAIL (`ImportError`/`AttributeError: parse_products`).

- [ ] **Step 3: Implement `parse_products`.** Create `scripts/ocado_search.py` with the function below. **Fill the field lookups from the fixture** captured in Task 1 (replace each `# <-- fixture path` with the real key from the sample). The output keys are fixed by the schema; only the *input* lookups are fixture-derived.
```python
#!/usr/bin/env python3
"""Search Ocado's product API and print products as JSON. Requires a UK IP."""

def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def parse_products(raw):
    # Locate the product array in the response (fixture-derived path).
    items = raw["products"] if isinstance(raw, dict) else raw   # <-- fixture path
    out = []
    for it in items:
        out.append({
            "name":        str(it.get("name", "")),             # <-- fixture path
            "brand":       str(it.get("brand", "") or ""),      # <-- fixture path
            "price":       _num(it.get("price")),               # <-- fixture path
            "currency":    "GBP",
            "pricePerUnit": str(it.get("unitPrice", "") or ""), # <-- fixture path
            "packSize":    str(it.get("packSize", "") or ""),   # <-- fixture path
            "inStock":     bool(it.get("available", False)),    # <-- fixture path
            "rating":      (None if it.get("rating") in (None, "") else _num(it.get("rating"))),
            "reviewCount": int(_num(it.get("reviewCount"))),    # <-- fixture path
            "productId":   str(it.get("id", "")),               # <-- fixture path
            "sku":         str(it.get("sku", "") or ""),        # <-- fixture path
            "url":         str(it.get("url", "") or ""),        # <-- fixture path
        })
    return out
```

- [ ] **Step 4: Run tests to green**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data/scripts"
python3 -m pytest tests/test_parse.py -q
```
Expected: PASS. If a field is missing/renamed, adjust the fixture path (not the output key) until green.

- [ ] **Step 5: Add one value assertion** pinning a known product from the fixture (guards against silent shape drift), e.g.:
```python
def test_first_product_values_match_fixture():
    raw = json.load(open(FIXTURE))
    p = parse_products(raw)[0]
    assert p["currency"] == "GBP"
    assert p["url"].startswith("https://www.ocado.com")
```
Run again; expect PASS.

- [ ] **Step 6: Commit**
```bash
git add scripts/ocado_search.py scripts/tests/test_parse.py
git commit -m "feat(scraper): parse_products maps Ocado API to output schema"
```

---

### Task 3: `fetch_search` — HTTP request with a runtime session

**Files:**
- Modify: `scripts/ocado_search.py` (add `fetch_search` + `build_url`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `fetch_search(query: str, limit: int, sort: str | None) -> dict | list` (the raw parsed JSON), and `build_url(query, limit, sort) -> str`.

- [ ] **Step 1: Implement `build_url` and `fetch_search`.** Use the endpoint + params from `CAPTURE_NOTES.md`. Establish a session first if the capture showed one is required (an initial GET to the homepage/search page to collect cookies), then request the API with a `CookieJar`. Realistic UA; 20s timeout.
```python
import json, urllib.parse, urllib.request, http.cookiejar

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SEARCH_ENDPOINT = "FILL_FROM_CAPTURE"   # e.g. https://www.ocado.com/webshop/api/v1/products/search
SORT_PARAM = {"price": "priceAscending", "rating": "customerRating",
              "price-per-unit": "pricePerAscending"}  # adjust to captured values

def build_url(query, limit, sort):
    params = {"query": query, "limit": limit}          # <-- adjust param names to capture
    if sort:
        params["sort"] = SORT_PARAM.get(sort, sort)    # <-- adjust param name to capture
    return SEARCH_ENDPOINT + "?" + urllib.parse.urlencode(params)

def _opener():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", USER_AGENT), ("Accept", "application/json")]
    return op

def fetch_search(query, limit, sort):
    op = _opener()
    # If the capture showed a session is needed, warm it up first:
    # op.open("https://www.ocado.com/", timeout=20).read()
    with op.open(build_url(query, limit, sort), timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

- [ ] **Step 2: Live smoke check** (needs UK IP + live site; not a CI test)
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data/scripts"
python3 -c "from ocado_search import fetch_search, parse_products; r=fetch_search('milk',3,None); print('products:', len(parse_products(r)))"
```
Expected: `products: 3` (or ≥1). If 0 or an HTTP error, revisit session/headers against `CAPTURE_NOTES.md`.

- [ ] **Step 3: Commit**
```bash
git add scripts/ocado_search.py
git commit -m "feat(scraper): fetch_search with runtime cookie session"
```

---

### Task 4: `main` — argparse CLI, JSON output, error handling

**Files:**
- Modify: `scripts/ocado_search.py` (add `main` + `__main__` guard)

**Interfaces:**
- Consumes: `fetch_search`, `parse_products`.

- [ ] **Step 1: Implement the CLI**
```python
import argparse, sys

def main(argv=None):
    ap = argparse.ArgumentParser(description="Search Ocado and print products as JSON.")
    ap.add_argument("query", help="search keyword, e.g. milk")
    ap.add_argument("--limit", type=int, default=30, help="max products (default 30)")
    ap.add_argument("--sort", choices=["price", "rating", "price-per-unit"], default=None)
    args = ap.parse_args(argv)
    try:
        products = parse_products(fetch_search(args.query, args.limit, args.sort))
    except Exception as e:                      # noqa: BLE001 - fail cleanly for the caller
        print(f"ocado_search: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if not products:
        print("ocado_search: no products returned (blocked, or non-UK IP?)", file=sys.stderr)
        return 2
    json.dump(products[:args.limit], sys.stdout, ensure_ascii=False, indent=2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify `--help` and arg parsing work (no network)**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data/scripts"
python3 ocado_search.py --help
```
Expected: usage text listing `query`, `--limit`, `--sort`.

- [ ] **Step 3: Live end-to-end check**
```bash
python3 ocado_search.py "milk" --limit 3
```
Expected: a JSON array of 3 products, each with the full schema; exit code 0 (`echo $?`).

- [ ] **Step 4: Commit**
```bash
git add scripts/ocado_search.py
git commit -m "feat(scraper): argparse CLI with JSON output and clean error exits"
```

---

### Task 5: `scripts/README.md` — usage and the UK-IP caveat

**Files:**
- Create: `scripts/README.md`

- [ ] **Step 1: Write the README** covering: what the script does; the exact run command and each flag; the **UK-IP requirement** (returns nothing otherwise); that it's stdlib-only (no install); the ToS/personal-use note; and how to refresh the fixture if Ocado changes its API (re-capture per Task 1).

- [ ] **Step 2: Verify it renders and links resolve**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"; test -f scripts/README.md && echo OK
```
Expected: `OK`.

- [ ] **Step 3: Commit**
```bash
git add scripts/README.md
git commit -m "docs(scraper): usage and UK-IP caveat"
```

---

### Task 6: Wire the scraper into do-the-shop Step 12

**Files:**
- Modify: `.claude/skills/do-the-shop/SKILL.md` (Step 12 + connector note)

- [ ] **Step 1: Add the preference order to Step 12.** Insert, at the top of the Step 12 per-item procedure, a source-selection rule:
```
For each item, get candidate products from the first available source:
1. **Local scraper (free, default):** run
   `python3 scripts/ocado_search.py "<item>" --limit 30 [--sort price|rating|price-per-unit]`
   via Bash and read the JSON array. Use it if it exits 0 with ≥1 product.
2. **Apify connector (fallback):** if the script is absent or returns nothing, call
   `mcp__apify-ocado__studio-amba--ocado-scraper` with maxProducts 10 and the GB
   residential proxy (as already documented below).
3. **Browser session:** if neither is available, let the browser pick products.
```

- [ ] **Step 2: Update the connector note** near the top of the skill to mention the local scraper as the default and Apify as the paid fallback (one sentence).

- [ ] **Step 3: Verify no absolute paths and the script path is repo-relative**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
grep -n "scripts/ocado_search.py" .claude/skills/do-the-shop/SKILL.md
grep -n "/Users/oliverfinn" .claude/skills/do-the-shop/SKILL.md; echo "abs-exit=$? (1=clean)"
```
Expected: the script path appears; no absolute paths (`abs-exit=1`).

- [ ] **Step 4: Commit**
```bash
git add .claude/skills/do-the-shop/SKILL.md
git commit -m "feat(do-the-shop): prefer free local scraper, Apify as fallback"
```

---

### Task 7: Push

- [ ] **Step 1: Confirm no secrets are tracked**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
git ls-files scripts | cat
grep -rInE "postcode|cookie:|authorization: bearer|set-cookie" scripts/tests/fixtures 2>/dev/null; echo "secret-exit=$? (1=clean)"
```
Expected: only script/test/fixture/readme files listed; no secret matches.

- [ ] **Step 2: Push**
```bash
git push
```
Expected: pushes to `origin/main`.

---

## Self-Review

**Spec coverage:** CLI + stdlib-only (Tasks 2–4), output schema (Global Constraints + Task 2), session/no-secrets (Tasks 1, 3, 7), default limit 30 (Task 4), skill integration preference order (Task 6), parser test + live smoke (Tasks 2–4), README + UK caveat (Task 5), lives in `scripts/` (all). Out-of-scope items (MCP wrapper, other retailers, category browse) correctly excluded.

**Placeholder scan:** the only deferred specifics are the endpoint URL and JSON field-paths, which are genuinely unknowable until Task 1's capture and are explicitly marked `# <-- fixture path` / `FILL_FROM_CAPTURE` with surrounding code complete — not vague TODOs.

**Type consistency:** `parse_products`, `fetch_search`, `build_url`, `main` signatures are consistent across Tasks 2–4; the output-schema keys match the test's `REQUIRED` set and the Global Constraints.
