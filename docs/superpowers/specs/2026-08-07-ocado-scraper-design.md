# Self-hosted Ocado scraper — design spec

Date: 2026-08-07

## Purpose
Provide a free, self-hosted alternative to the paid Apify Ocado actor for Step 12
product matching. It runs from the user's UK connection, so no residential proxy and no
per-shop cost. It emits the same product fields the `do-the-shop` skill already consumes,
so it drops into the existing flow.

## Approach
A small **Python 3 CLI script** (`scripts/ocado_search.py`) that replicates Ocado's own
product-search API request and prints a JSON array to stdout. Stdlib-only (`urllib`,
`json`) — no third-party dependencies. The skill calls it via Bash.

## CLI interface
```
python3 scripts/ocado_search.py "<query>" [--limit N] [--sort price|rating|price-per-unit]
```
- `<query>`: search keyword (e.g. `milk`). Required.
- `--limit N`: max products to return (default 10).
- `--sort`: optional ordering; maps to Ocado's sort param when available.
- Output: a JSON array to **stdout**. On failure: a clear message to **stderr** and a
  non-zero exit code (so the skill can detect failure and fall back).

## Output schema (one object per product)
Matches the fields the skill already reads, so Step 12 needs no field remapping:
`name` (str), `brand` (str), `price` (number, GBP), `currency` (str, "GBP"),
`pricePerUnit` (str, e.g. "£9.90/kg"), `packSize` (str), `inStock` (bool),
`rating` (number|null), `reviewCount` (number), `productId` (str), `sku` (str),
`url` (str). Missing values are `null`/empty rather than omitted.

## Session / anti-bot handling
The exact endpoint, query params, required headers, and any session/cookie or delivery
postcode requirement are taken from a **captured request** (the user's browser
"Copy as cURL"), obtained as the first implementation step. Principles:
- The script **establishes its own session at runtime** (an initial request to acquire
  any cookie/token) — it does NOT hardcode a captured cookie or token.
- **No captured secrets are committed.** Anything session-specific is fetched at run
  time; the repo contains only generic request logic.
- Polite pacing: a short delay between successive searches; a realistic User-Agent.
- If Ocado returns an empty/blocked response, the script exits non-zero with a clear
  message so the skill falls back to Apify or the browser.

## Skill integration (Step 12)
`do-the-shop` Step 12 gains a preference order for product matching:
1. **Local script** (`scripts/ocado_search.py`) if present and it returns results — the
   free default.
2. **Apify connector** (`studio-amba/ocado-scraper`) as automatic fallback.
3. **Browser session** picks products if neither is available.
The rest of Step 12 (choosing the preferred product, honouring `SHOP_PREFS`, storing
alternatives by code) is unchanged.

## Testing
- **Parser unit test** against a saved fixture — a real captured API response committed
  as `scripts/tests/fixtures/ocado_search_sample.json` (scrubbed of any session data) —
  asserting the parser produces the output schema with correct types. Deterministic, no
  network.
- **Live smoke test** (manual/opt-in): `ocado_search.py "milk" --limit 3` returns ≥1
  product with all required fields populated. Not run in CI (needs a UK IP + live site).

## Files
- Create: `scripts/ocado_search.py` (the CLI).
- Create: `scripts/README.md` (usage + the "must run from a UK IP" note).
- Create: `scripts/tests/test_parse.py`, `scripts/tests/fixtures/ocado_search_sample.json`.
- Modify: `.claude/skills/do-the-shop/SKILL.md` (Step 12 preference order + connector note).

## Out of scope
- A long-running server or MCP wrapper (CLI-only for now; possible later).
- Scraping retailers other than Ocado.
- Category-browse mode (search-by-keyword only for v1; add later if needed).

## Risks / caveats
- **Unofficial API:** Ocado can change it without notice; the parser then needs updating.
  Mitigated by the fixture test (fast to see what changed) and graceful fallback.
- **UK-only:** returns nothing from a non-UK IP; documented in `scripts/README.md`.
- **Terms of Service:** personal, low-volume use only; already noted in the repo README.
