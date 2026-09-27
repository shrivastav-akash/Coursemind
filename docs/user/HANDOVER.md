# CourseMind — Handover

Filled at the end of every session so the next one starts cold without questions. Replace the contents each time; git history keeps the old ones.

**Date:** 2026-09-27
**Step:** 1 — Repo and backend skeleton
**Status:** done, awaiting owner review and first commit (not committed)

## Changed
- `git init -b main`; `.gitignore` (ignores `.env`, `.venv/`, caches, frontend build output, `docs/user/CourseMind_build_plan.md`).
- `backend/`: venv, pinned `requirements.txt` (fastapi 0.141.1, uvicorn[standard] 0.54.0, python-dotenv 1.2.3) and `requirements-dev.txt` (pytest 9.1.1, httpx 0.28.1), `.python-version`, `.env.example`, `pytest.ini`.
- `app/config.py` (env vars, fixed ids, limits, refusal, model names; bad `RETRIEVAL_MODE` or non-int numbers fail at import), `app/schemas.py` (copied from BACKEND_SCHEMA §8), `app/main.py` (CORS + `GET /health`).
- `tests/test_api.py::test_health`.
- Root `README.md`, `CLAUDE.md` (Tier: full, doc locations).
- Docs: fixed paths/links after the `docs/app` + `docs/user` split (see DECISIONS).

## Verified
- `pytest -q` → `1 passed`.
- `curl localhost:8000/health` → `{"status":"ok"}`; `/docs` → 200; OpenAPI lists `/health` only.
- CORS preflight from `http://localhost:3000` allowed with `X-Workspace-Id`; unknown origin → 400.
- `git status` does not list `.env`, `.venv/`, or the build plan (`git check-ignore` confirms).

## Pending
- Owner OK, then first commit: `chore: repo and backend skeleton`.
- Test warning: Starlette 1.7 says "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." Swapping `httpx` for `httpx2` in `requirements-dev.txt` is a dependency change, so it needs owner approval.
- Secrets (`GROQ_API_KEY`, `QDRANT_*`) are not required at startup yet. Add a fail-fast check when steps 6 and 8 start using them.

## Known issues
- None besides the httpx deprecation warning.

## Next step
- Step 2 — PDF parser and chunker (adds `pypdfium2`, `langchain-text-splitters`, dev `fpdf2`). Starts only after owner review.
