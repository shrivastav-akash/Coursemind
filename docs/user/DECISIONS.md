# CourseMind — Decisions

One entry per decision made during the build, newest at the bottom. Decisions made before the build live in PRD, TRD, and the other approved docs; this log records what changes or gets settled after that.

**Entry format**

```
## YYYY-MM-DD — Short title
**Context:** what forced a choice
**Decision:** what we chose
**Why:** the deciding reason (numbers if any)
**Affects:** files / docs updated
```

---

## 2026-09-27 — Docs split into docs/app and docs/user
**Context:** The owner moved the docs into `docs/app/` (product and technical specs) and `docs/user/` (constraints, decisions, handover, private build plan). Step 1's `.gitignore` still pointed at `docs/CourseMind_build_plan.md`, so the private plan would have been committed.
**Decision:** Keep the split. Ignore the exact path `docs/user/CourseMind_build_plan.md`. Fix relative links in IMPLEMENTATION_PLAN. Add a root `CLAUDE.md` that declares `Tier: full` and lists where the docs live.
**Why:** The owner prefers the split and chose the exact-path ignore. Full tier matches the doc set already in place.
**Alternatives:** Ignore the file by name anywhere (survives future moves; not chosen). Flatten back to `docs/` (not chosen).
**Affects:** `.gitignore`, `CLAUDE.md`, IMPLEMENTATION_PLAN (links, `.gitignore` snippet, step 1 check), CONSTRAINTS (path), ARCHITECTURE (folder table).

## 2026-09-27 — pytest.ini for the import path
**Context:** `pytest -q` from `backend/` could not import `app` (pytest puts `tests/` on `sys.path`, not `backend/`).
**Decision:** Add `backend/pytest.ini` with `pythonpath = .`.
**Why:** One line of config. No `conftest.py` hacks and no package install. Later steps can register the `live` marker in the same file.
**Affects:** `backend/pytest.ini`, ARCHITECTURE.
