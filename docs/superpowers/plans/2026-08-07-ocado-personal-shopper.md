# Ocado personal shopper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Shop Data folder + global skills into a self-contained, public GitHub repo (`ocado-personal-shopper`) that friends can clone and run in Claude Code, with the author's personal data gitignored.

**Architecture:** Repo is git-init'd in place at the current Shop Data folder. Skills move into `.claude/skills/`; all data moves under `data/` and skills reference it by repo-relative paths. Personal content is gitignored; generic examples + `*.example.md` templates are committed.

**Tech Stack:** Markdown skills, git, GitHub `gh` CLI. No build/runtime.

## Global Constraints

- Repo root = `/Users/oliverfinn/Dropbox/Documents/Shop Data` (init in place; do NOT relocate).
- Repo name on GitHub: `ocado-personal-shopper`, **public**.
- No hardcoded home paths in committed files — skills use repo-relative `data/…`.
- Personal data (author's real recipes, shopping-lists, consumables, recipe-urls, shopping-preferences, `.mcp.json`) must NEVER be tracked by git.
- Commit personal-data-safety is verified with `git ls-files` before any push.

---

### Task 1: Reorganise data under `data/` and write `.gitignore`

**Files:**
- Create dir: `data/`, move existing data into it
- Create: `.gitignore`
- Create: `data/shopping-lists/.gitkeep`

- [ ] **Step 1: Create data/ and move working data into it**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
mkdir -p data
mv recipes data/recipes
mv shopping-lists data/shopping-lists
mv consumables.md data/consumables.md
mv recipe-urls.md data/recipe-urls.md
mv shopping-preferences.md data/shopping-preferences.md
touch data/shopping-lists/.gitkeep
```

- [ ] **Step 2: Verify the new structure**
```bash
ls -1 data && echo "---" && ls -1 data/recipes | head
```
Expected: `data/` contains `recipes  shopping-lists  consumables.md  recipe-urls.md  shopping-preferences.md`; `data/recipes` lists the author's recipe files + `README.md`.

- [ ] **Step 3: Write `.gitignore`**
```
# personal recipes — keep README + generic examples
data/recipes/*.md
!data/recipes/README.md
!data/recipes/example-*.md
# personal shopping lists — keep the folder only
data/shopping-lists/*
!data/shopping-lists/.gitkeep
# personal working config — templates committed as *.example.md
data/consumables.md
data/recipe-urls.md
data/shopping-preferences.md
# secrets / local MCP config
.mcp.json
.env
# OS noise
.DS_Store
```

- [ ] **Step 4: (No commit yet — git not initialised until Task 5.)**

---

### Task 2: Bring the skills into the repo and make paths repo-relative

**Files:**
- Create: `.claude/skills/do-the-shop/` (+ `references/`), `.claude/skills/collect-recipes/`, `.claude/skills/describe-recipe/` (copied from `~/.claude/skills/`)
- Modify: every `SKILL.md` + `references/*.md` to replace the absolute path

- [ ] **Step 1: Copy the three skills in from the global location**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
mkdir -p .claude/skills
cp -R ~/.claude/skills/do-the-shop .claude/skills/do-the-shop
cp -R ~/.claude/skills/collect-recipes .claude/skills/collect-recipes
cp -R ~/.claude/skills/describe-recipe .claude/skills/describe-recipe
```

- [ ] **Step 2: List every absolute-path occurrence to be replaced**
```bash
grep -rn "/Users/oliverfinn/Dropbox/Documents/Shop Data" .claude/skills
```
Expected: several matches across the three SKILL.md files (data-location blocks, `RECIPES_DIR`, `CONSUMABLES`, `URL_LIBRARY`, `SHOP_PREFS`, shopping-lists references).

- [ ] **Step 3: Replace the absolute base path with the repo-relative `data/`**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
grep -rl "/Users/oliverfinn/Dropbox/Documents/Shop Data" .claude/skills \
  | xargs sed -i '' 's#/Users/oliverfinn/Dropbox/Documents/Shop Data/#data/#g; s#/Users/oliverfinn/Dropbox/Documents/Shop Data#data#g'
```

- [ ] **Step 4: Verify no absolute paths remain, and the relative tokens read correctly**
```bash
grep -rn "/Users/oliverfinn" .claude/skills; echo "exit=$?"
grep -rn "data/recipes\|data/consumables.md\|data/recipe-urls.md\|data/shopping-preferences.md\|data/shopping-lists" .claude/skills | head
```
Expected: first grep prints nothing (`exit=1`); second grep shows the repo-relative tokens now in place.

- [ ] **Step 5: Fix any now-awkward wording by hand**
Open each `SKILL.md`; where a line read "Data location: `data`" ensure it reads "Data location (repo-relative): `data/`". Confirm the `RECIPES_DIR`/`CONSUMABLES`/`URL_LIBRARY`/`SHOP_PREFS` bullets now point at `data/…`. Edit inline as needed.

---

### Task 3: Create generic starter content

**Files:**
- Create: `data/recipes/example-porridge.md`, `data/recipes/example-tomato-pasta.md`, `data/recipes/example-cheese-sandwich.md`
- Create: `data/consumables.example.md`, `data/recipe-urls.example.md`, `data/shopping-preferences.example.md`

- [ ] **Step 1: Write three generic example recipes** (one per meal type), each following `data/recipes/README.md` format. Example (`example-porridge.md`):
```markdown
---
name: Example porridge
type: weekday breakfast
base_servings: 1
source: described
---

## Ingredients (per 1 serving)
- 50 g porridge oats
- 300 ml milk
- 10 g honey
```
Repeat with `example-tomato-pasta.md` (`type: weekday dinner`, oats→pasta/passata/etc.) and `example-cheese-sandwich.md` (`type: lunch`). Keep them neutral — no author-specific brands.

- [ ] **Step 2: Write `data/consumables.example.md`** — the generic section structure (Bathroom / Kitchen & cleaning / Laundry / Staples) with common items and `Milk (default: yes)`; no author-specific extras.

- [ ] **Step 3: Write `data/recipe-urls.example.md`** — the browse-index header/template with the ENTRY TEMPLATE comment and zero entries.

- [ ] **Step 4: Write `data/shopping-preferences.example.md`** — Store (Ocado), Choosing products (price+reviews, size-up-never-down, bulk consumables if cheaper), Substitutions (flag for approval), and an empty "Dietary / brands / packaging" section. NO author brand choices.

- [ ] **Step 5: Verify examples exist and are well-formed**
```bash
ls -1 data/recipes/example-*.md data/*.example.md
head -6 data/recipes/example-porridge.md
```
Expected: all six files listed; frontmatter valid.

---

### Task 4: Write `README.md` and `.mcp.json.example`

**Files:**
- Create: `README.md`, `.mcp.json.example`

- [ ] **Step 1: Write `.mcp.json.example`**
```json
{
  "mcpServers": {
    "apify-ocado": {
      "type": "http",
      "url": "https://mcp.apify.com/?actors=studio-amba/ocado-scraper",
      "headers": { "Authorization": "Bearer YOUR_APIFY_TOKEN" }
    }
  }
}
```

- [ ] **Step 2: Write `README.md`** covering, in order:
  1. What it is (a Claude Code skill suite that plans a weekly shop end-to-end).
  2. Quick start: clone; `cp` each `data/*.example.md` → its working name (`consumables.md`, `recipe-urls.md`, `shopping-preferences.md`); open the repo in Claude Code; run "do the shop".
  3. How it works — the do-the-shop step flow (recipes → scale → verify → compile → deduct → optional Ocado product-match → browser basket → verify → feedback).
  4. Optional Apify connector: copy `.mcp.json.example` → `.mcp.json`, add your Apify token; note the **GB residential proxy** requirement and the **$5-balance-to-launch** caveat; ~£1–2/shop.
  5. Model tips: Opus for planning; Sonnet for the browser session and checker agents.
  6. Data & privacy: personal recipes/lists/preferences are gitignored; only examples ship.
  7. Disclaimer: for personal, low-volume use; scraping is subject to Ocado's Terms of Service.

- [ ] **Step 3: Verify**
```bash
test -f README.md && test -f .mcp.json.example && echo OK
python3 -c "import json;json.load(open('.mcp.json.example'))" && echo "json valid"
```
Expected: `OK` and `json valid`.

---

### Task 5: Initialise git and make the first commit (privacy gate)

**Files:** none (git operations)

- [ ] **Step 1: Init and stage**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
git init
git add .
```

- [ ] **Step 2: PRIVACY GATE — verify no personal data is staged**
```bash
git status --short | grep -E "data/recipes/(burritos|mapo-eggplant|granola|herby-frittata|carrot-lox|tuna-sweetcorn-pittas|cheese-and-coleslaw-sandwich|one-pot|smoky-tomato)|data/shopping-lists/2026-|data/consumables.md$|data/recipe-urls.md$|data/shopping-preferences.md$|\.mcp\.json$"; echo "exit=$?"
```
Expected: prints nothing (`exit=1`). If ANY personal file appears, STOP and fix `.gitignore` before continuing.

- [ ] **Step 3: Confirm the intended files ARE staged**
```bash
git ls-files | grep -E "example-|\.example\.md|\.gitkeep|README|\.claude/skills|\.mcp\.json\.example|\.gitignore|docs/superpowers" | head -40
```
Expected: skills, examples, templates, README, gitignore, spec/plan docs all listed.

- [ ] **Step 4: Commit**
```bash
git commit -m "Initial commit: Ocado personal shopper skill suite + data scaffold

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Create the public GitHub repo and push

**Files:** none (gh operations)

- [ ] **Step 1: Confirm gh is authenticated**
```bash
gh auth status
```
Expected: logged in. If not, stop and tell the user to run `gh auth login`.

- [ ] **Step 2: Create the public repo and push**
```bash
cd "/Users/oliverfinn/Dropbox/Documents/Shop Data"
gh repo create ocado-personal-shopper --public --source=. --remote=origin --push
```

- [ ] **Step 3: Verify remote + pushed tree contains no personal data**
```bash
gh repo view ocado-personal-shopper --json url -q .url
git ls-remote --heads origin
```
Expected: repo URL printed; a `main` (or `master`) head exists. Spot-check the URL in a browser: only skills, examples, templates, README, docs.

---

### Task 7: Retire the global skill copies (source of truth = repo)

**Files:** delete `~/.claude/skills/{do-the-shop,collect-recipes,describe-recipe}`

- [ ] **Step 1: Confirm the repo copies exist first**
```bash
ls -1 "/Users/oliverfinn/Dropbox/Documents/Shop Data/.claude/skills"
```
Expected: `collect-recipes  describe-recipe  do-the-shop`.

- [ ] **Step 2: Remove the global copies**
```bash
rm -rf ~/.claude/skills/do-the-shop ~/.claude/skills/collect-recipes ~/.claude/skills/describe-recipe
```

- [ ] **Step 3: Verify**
```bash
ls -1 ~/.claude/skills 2>/dev/null | grep -E "do-the-shop|collect-recipes|describe-recipe"; echo "exit=$?"
```
Expected: prints nothing (`exit=1`). From now on, shopping is run by opening the repo in Claude Code.

---

## Self-Review

**Spec coverage:** repo layout (Tasks 1–4), portability fix (Task 2), gitignore/personal-data (Tasks 1, 5), starter content (Task 3), README + first-run + Apify docs (Task 4), GitHub public (Task 6), author-machine migration + retire globals (Tasks 1, 7). Out-of-scope items (custom scraper, memory pointers) correctly excluded.

**Placeholder scan:** example recipe content and README sections are specified concretely; no TBD/TODO left.

**Consistency:** the absolute path string is identical everywhere; `data/…` token names match the spec's `RECIPES_DIR`/`CONSUMABLES`/`URL_LIBRARY`/`SHOP_PREFS` mapping.
