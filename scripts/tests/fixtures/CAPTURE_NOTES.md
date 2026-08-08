# Ocado search API — capture notes

Reverse-engineered from a browser "Copy as cURL" on 2026-08-07. No secrets here.

## Endpoint
`GET https://www.ocado.com/api/webproductpagews/v6/product-pages/search`

## Query params
- `q` — the search keyword (e.g. `milk`). **This is the search term.**
- `maxProductsToDecorate` — how many products get full data (name/price/etc.); the rest
  come back as bare ids. Use this as the effective result cap (was 50 in the capture).
- `maxPageSize` — total page size (was 300).
- `tag=web`, `includeAdditionalPageInfo=true` — send as-is.

## Headers (minimal set that works)
- `accept: application/json; charset=utf-8`
- `accept-language: en-GB,en-US;q=0.9`
- `ecom-request-source: web`
- `referer: https://www.ocado.com/search?q=<query>`
- a normal desktop `user-agent`

## Session / anti-bot — SOLVED, no token needed
Ocado sits behind AWS WAF, but the search endpoint does **not** require the
`aws-waf-token` cookie. A cookie-free warm-up works: `GET https://www.ocado.com/` with a
`CookieJar` sets `global_sid`, `AWSALB`, `VISITORID`; the subsequent API call then
returns HTTP 200 with products. No JS challenge, no proxy (UK IP required).

## Response shape
```
{
  "productGroups": [
    { "type": "featured|favorite|cluster", "name": ...,
      "decoratedProducts": [ <product>, ... ],
      "otherProductIds": [ "<id>", ... ] },
    ...
  ],
  "metadata": {...}, "additionalPageInfo": {...}, "missedPromotions": {...}
}
```
- Real results are the `decoratedProducts` across groups. `type: "featured"` is
  sponsored (skip). Aggregate the rest, dedupe by `retailerProductId`, preserve order.
- Only `maxProductsToDecorate` products are decorated in total; others are id-only.

### Per-product fields (→ our output schema)
- `retailerProductId` (numeric, e.g. "78920011")  → `productId`  (used in the URL)
- `productId` (UUID)                               → `sku`
- `name`, `brand`                                  → `name`, `brand`
- `price` = `{amount:"1.75", currency:"GBP"}`      → `price` (float), `currency`
- `unitPrice` = `{price:{amount:"77.0",currency:"GBX"}, unitName:"PER_LITRE"}`
                                                   → `pricePerUnit` (format "£0.77/litre")
- `packSizeDescription` ("2.272L")                 → `packSize`
- `available` (bool)                               → `inStock`
- `ratingSummary` = `{overallRating:"3.9", count:179}` → `rating` (float|null), `reviewCount`
- URL: `https://www.ocado.com/products/<name-slug>/<retailerProductId>`

Note `unitPrice.price.amount` is in **GBX (pence)** — divide by 100 for pounds.
`unitName` values seen: `PER_LITRE`, `PER_KG`, `PER_100_GRAM`, `PER_EACH`.

## Refreshing this fixture
If Ocado changes the shape and the parser test fails, re-capture per Task 1 and rebuild
`ocado_search_sample.json` (session-free response, trimmed).
