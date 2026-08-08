# Ocado search scraper (`ocado_search.py`)

A tiny, free, self-hosted alternative to the paid Apify actor. It queries Ocado's own
product-search API and prints products as JSON in the same shape the `do-the-shop` skill
consumes. **Standard library only — nothing to install.**

## Requirements
- **Python 3** (any recent version).
- **A UK IP address.** Ocado geo-restricts its catalogue; from outside the UK you'll get
  no results. No proxy is used or needed — it runs on your own connection.

## Usage
```bash
python3 scripts/ocado_search.py "<search term>" [--limit N] [--sort KEY]
```
- `--limit N` — max products to return (default **30**). It's free, so a big pool is fine.
- `--sort` — `price` (low→high), `rating` (high→low), or `price-per-unit` (low→high).
  Sorting is done locally on the results.

Output is a JSON array on stdout; each product has:
`name, brand, price, currency, pricePerUnit, packSize, inStock, rating, reviewCount,
productId, sku, url`. On failure it prints a message to stderr and exits non-zero
(exit 1 = error, 2 = no products), so the skill can fall back to Apify or the browser.

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
No test framework needed:
```bash
python3 scripts/tests/test_parse.py
```
Runs the parser against a saved, session-free fixture (`tests/fixtures/`).

## Troubleshooting
- **`CERTIFICATE_VERIFY_FAILED`** — the script auto-loads a system CA bundle, so this is
  usually handled. If it still appears on a python.org macOS install, run the bundled
  `Install Certificates.command` (in your `/Applications/Python 3.x/` folder) once.
- **Empty results / exit 2** — check you're on a UK IP.
- **Parser errors after an Ocado change** — re-capture per `tests/fixtures/CAPTURE_NOTES.md`
  and refresh the fixture.

## Legal
For personal, low-volume use. Scraping Ocado is subject to Ocado's Terms of Service.
