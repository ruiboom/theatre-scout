# Question Log

Decisions taken autonomously during the build that the user should review later. Each entry: what came up, the recommendation taken, and why.

---

## M0 — git init

**Question**: BUILD.md calls for "small commits", but the folder wasn't a git repo. Initialize one?

**Decision taken**: `git init` and committing per milestone. Used `main` as the default branch. No remote configured.

**Why**: Small-focused commits are part of the working principles you approved. If you'd rather not have version control, just `rm -rf .git`.

---

## M0 — uv vs pip

**Question**: BUILD.md specifies uv as the package manager. uv is installed (0.10.2). Lockfile committed?

**Decision taken**: Yes — `uv.lock` is committed. Standard practice for reproducible installs.

**Why**: Without a lockfile, every fresh checkout pulls latest matching versions and adapters can break silently when a parser library changes behavior.

---

## M1 — fringe count discrepancy (CLAUDE.md said 67, actual is 68)

**Question**: My CLAUDE.md heading said `fringe — 18 theatres` but the bullet listed 19 names. Total should be 68, not 67.

**Decision taken**: Updated CLAUDE.md and BUILD.md to 68 total / 19 fringe. This matches the venues you originally provided.

**Why**: Off-by-one in the original count, not a venue you intended to drop. If you actually want to drop one, tell me which.

---

## M1 — slugs for ATG venues

**Question**: New Wimbledon Theatre and Richmond Theatre both run on `atgtickets.com`. What URL goes in `theatres.yaml`?

**Decision taken**: Used venue-specific paths I'm fairly sure of:
- `https://www.atgtickets.com/venues/new-wimbledon-theatre/`
- `https://www.atgtickets.com/venues/richmond-theatre/`

**Why**: ATG uses a consistent `/venues/<slug>/` URL pattern. If wrong, the adapter for those will fail loudly with a 404 and we fix the URL.

---

## M1 — slugs for Troubadour venues

**Question**: Both Troubadour venues use `troubadour.com`. Same URL?

**Decision taken**: Same homepage URL (`https://troubadour.com`) for both. Adapter will distinguish by venue when scraping.

**Why**: Less guessing. If Troubadour has separate venue pages, the adapter will navigate to them; the homepage is just the entry point.

---

## M1 — Sadler's Wells East and Soho Walthamstow

**Question**: Sadler's Wells lists "+ Sadler's Wells East, Stratford" and Soho lists "+ Soho Theatre Walthamstow, E17". Separate entries?

**Decision taken**: Rolled into the main entry. Each adapter can scrape both venues if listings cover them.

**Why**: They're operationally one organisation with shared programming. Keeping them separate would duplicate adapter code. If you'd rather have them as separate slugs, easy to split later.

---

## M0 — Python version floor

**Question**: BUILD.md says "Python 3.11+". System has 3.12.3. Pin floor at 3.11 or 3.12?

**Decision taken**: `requires-python = ">=3.11"` to match the spec.

**Why**: 3.11 has all the type-system features we need; no reason to exclude it.

---
