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

## M0 — Python version floor

**Question**: BUILD.md says "Python 3.11+". System has 3.12.3. Pin floor at 3.11 or 3.12?

**Decision taken**: `requires-python = ">=3.11"` to match the spec.

**Why**: 3.11 has all the type-system features we need; no reason to exclude it.

---
