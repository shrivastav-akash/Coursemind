# CourseMind

Tier: full

Multi-format, multi-document RAG study assistant with page/slide/section citations. Stack: FastAPI + Python 3.12 backend, Next.js + TypeScript static frontend, Qdrant Cloud, Groq.

## Docs
- `docs/app/`: PRD, TRD, APP_FLOW, UI_UX_BRIEF, BACKEND_SCHEMA, IMPLEMENTATION_PLAN, ARCHITECTURE
- `docs/user/`: CONSTRAINTS, DECISIONS, HANDOVER
- `docs/user/CourseMind_build_plan.md` is private and git-ignored. Never commit or quote it.

At session start read `docs/app/ARCHITECTURE.md`, `docs/user/CONSTRAINTS.md`, `docs/user/HANDOVER.md`.
Build order and per-step rules: `docs/app/IMPLEMENTATION_PLAN.md`. One step per session; stop for review.

## Commands
```bash
cd backend && .venv/bin/pytest -q
cd backend && .venv/bin/uvicorn app.main:app --reload
```
