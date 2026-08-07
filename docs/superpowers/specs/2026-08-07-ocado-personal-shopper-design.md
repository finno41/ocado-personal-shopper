# Ocado personal shopper — design spec

Date: 2026-08-07

## Purpose
Package the weekly-shop skill suite and its data scaffold into a shareable,
self-contained repo that friends can clone and run in Claude Code, while keeping the
author's personal data private.

## Approach
Self-contained repo: the three skills live in `.claude/skills/`, all data lives under
`data/`, and the skills reference data by **repo-relative paths**. It is run by opening
the repo in Claude Code (skills are discovered from the project's `.claude/skills/`).
This removes every hardcoded home path, so no per-user configuration is needed.

## Repo layout
```
ocado-personal-shopper/            (== the existing Shop Data folder, git-init'd in place)
├── README.md
├── .gitignore
├── .mcp.json.example
├── docs/superpowers/specs/2026-08-07-ocado-personal-shopper-design.md
├── .claude/skills/
│   ├── do-the-shop/            (SKILL.md + references/)
│   ├── collect-recipes/
│   └── describe-recipe/
└── data/
    ├── recipes/
    │   ├── README.md
    │   └── example-*.md            (2–3 generic sample recipes)
    ├── shopping-lists/.gitkeep
    ├── consumables.example.md
    ├── recipe-urls.example.md
    └── shopping-preferences.example.md
```

## Portability fix
Replace every absolute `/Users/oliverfinn/Dropbox/Documents/Shop Data/…` reference in
the three skills (and `references/verification.md`) with the repo-relative `data/…`.
Affected tokens: `RECIPES_DIR` → `data/recipes/`, `CONSUMABLES` → `data/consumables.md`,
`URL_LIBRARY` → `data/recipe-urls.md`, `SHOP_PREFS` → `data/shopping-preferences.md`,
shopping-lists dir → `data/shopping-lists/`. Grep the skills for the absolute path to
catch every occurrence.

## Data & gitignore
Working data (the author's real recipes, shopping lists, preferences, consumables,
recipe-urls) lives under `data/` and is **gitignored** so it never reaches the public
repo. Committed instead: the folder structure, `data/recipes/README.md`, `example-*.md`
recipes, `*.example.md` templates, and `data/shopping-lists/.gitkeep`.

`.gitignore` rules:
```
# personal recipes — keep README + generic examples
data/recipes/*.md
!data/recipes/README.md
!data/recipes/example-*.md
# personal shopping lists — keep the folder only
data/shopping-lists/*
!data/shopping-lists/.gitkeep
# personal working config — templates are committed as *.example.md
data/consumables.md
data/recipe-urls.md
data/shopping-preferences.md
# secrets / local MCP config
.mcp.json
.env
# OS noise
.DS_Store
```
Note: the `docs/superpowers/specs/` design doc IS committed (it documents the project);
nothing under `docs/` is ignored.

## Starter content
2–3 generic example recipes named `example-*.md` (e.g. porridge, simple pasta) that
demonstrate the format without exposing the author's collection. Example templates for
`consumables`, `recipe-urls`, and `shopping-preferences` seeded with neutral defaults
(the shopping-preferences example keeps the generic price/reviews/size rules but not the
author's brand choices).

## First-run for a friend
Documented in README, with an optional `setup.sh`:
1. Clone the repo.
2. Copy each `*.example.md` → its working filename; create `data/shopping-lists/`.
3. Open the repo in Claude Code.
4. (Optional) add the Apify Ocado connector for automated product matching.
5. Run "do the shop".

## Apify connector (documented, optional)
README explains adding `studio-amba/ocado-scraper` via the Apify MCP with the **GB
residential proxy** requirement and the **$5-balance-to-launch** caveat. A
`.mcp.json.example` shows the entry with a token placeholder; the real `.mcp.json` is
gitignored.

## Author's machine
- `git init` in place at the existing `Shop Data` folder (in Dropbox).
- Migrate existing data into `data/` (gitignored working copy).
- Retire the global `~/.claude/skills/` copies so the repo is the single source of
  truth; shopping is launched by opening the repo. (Reversible — git retains them.)

## GitHub
Public repo named `ocado-personal-shopper`, created with `gh`.

## Out of scope
- Building a custom (non-Apify) scraper — a possible later project.
- Updating the author's Claude memory pointers to the new location — minor, later.

## Risks / caveats
- A git repo inside Dropbox can occasionally conflict under heavy concurrent use; fine
  for light use. Flagged, not blocking ("leave it where it is for now").
- Skill discovery requires running Claude Code from inside the repo directory.
