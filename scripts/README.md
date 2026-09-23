# Ocado search scraper (`ocado_search.py`)

A tiny, free, self-hosted Ocado product search. It queries Ocado's own product-search
API and prints products as JSON in the shape the `do-the-shop` skill consumes. **Standard
library only — nothing to install.** (No paid service such as Apify is used.)

> The skill's product-matching step is currently **paused** (see the main README), so
> the skill doesn't call this script right now. It still works standalone.

## Requirements
- **Python 3** (any recent version).
- **A UK IP address.** Ocado geo-restricts its catalogue; from outside the UK you'll get
  no results. No proxy is used or needed — it runs on your own connection.

## Usage

### Batch mode (use this for a whole shop)
```bash
python3 scripts/ocado_search.py --batch items.json [--gap 2]
```
Runs every query through **one** warmed session, reusing the cookie jar, with a small
gap between requests (`--gap`, default 2 s). `items.json` is a list of
`{"label", "query", "sort", "limit"}` objects (`label`, `sort` and `limit` optional);
pass `-` to read the list from stdin. Output is a JSON object keyed by label →
`{query, products: [...]}`.

**Don't fire lots of single queries in a row instead.** Each one starts a fresh cold
session, and a burst of those trips Ocado's anti-bot: the API starts returning
**HTTP 202 with an empty body** — a soft IP block that takes ~20–30 minutes of quiet to
clear. One batch, one session.

### Single query (one-offs only)
```bash
python3 scripts/ocado_search.py "<search term>" [--limit N] [--sort KEY]
```
- `--limit N` — max products to return (default **30**). It's free, so a big pool is fine.
- `--sort` — `price` (low→high), `rating` (high→low), or `price-per-unit` (low→high).
  Sorting is done locally on the results.

Output is a JSON array on stdout; each product has:
`name, brand, price, currency, pricePerUnit, packSize, inStock, rating, reviewCount,
productId, sku, url`. On failure it prints a message to stderr and exits non-zero
(exit 1 = error, 2 = no products), so the caller can fall back to the browser.

### Examples
```bash
python3 scripts/ocado_search.py "milk" --limit 5
python3 scripts/ocado_search.py "cashews" --sort price-per-unit
python3 scripts/ocado_search.py "greek yoghurt" --sort rating --limit 10
```

## How it works
1. Warms up a cookie session with a plain GET to `ocado.com` (sets the session cookies
   the API needs — no AWS-WAF token or JS challenge required).
2. Calls `…/api/webproductpagews/v6/product-pages/search?q=<term>`.
3. Flattens the response: aggregates real results, skips sponsored (`featured`) ads,
   dedupes, and maps to the output schema. See `tests/fixtures/CAPTURE_NOTES.md`.

## Tests
No test framework needed — from the repo root:
```bash
python3 -m unittest discover -s scripts/tests -t .
```
This runs the scraper's parser tests against a saved, session-free fixture
(`tests/fixtures/`) along with the `recipe_engine.py` tests.

## Troubleshooting
- **`CERTIFICATE_VERIFY_FAILED`** — the script auto-loads a system CA bundle, so this is
  usually handled. If it still appears on a python.org macOS install, run the bundled
  `Install Certificates.command` (in your `/Applications/Python 3.x/` folder) once.
- **Empty results / exit 2** — check you're on a UK IP. If you are, you've probably hit
  the anti-bot soft block (HTTP 202, empty body): stop making requests for ~20–30
  minutes, then use batch mode.
- **Parser errors after an Ocado change** — re-capture per `tests/fixtures/CAPTURE_NOTES.md`
  and refresh the fixture.

## Legal
For personal, low-volume use. Scraping Ocado is subject to Ocado's Terms of Service.
