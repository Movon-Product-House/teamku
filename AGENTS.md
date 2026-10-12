# AGENTS.md

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues (`Movon-Product-House/teamku`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Front-end (`apps/web`)

Conventions, structure and the page-migration recipe: `apps/web/README.md`. Run `npm run check` in `apps/web` before pushing. Building a v2 revamp screen from `mockups/`: use the `slice-screen` skill (`.claude/skills/slice-screen/`).
Visual tokens and rules: `DESIGN.md`; product context (users, tone, principles): `PRODUCT.md`.

## API (`apps/api`)

Conventions, module layout, tenancy rules and how to add a module + migration: `apps/api/README.md`. Architecture decisions: `docs/adr/0002-backend-api-architecture.md`. Run `scripts/check.sh` in `apps/api` before pushing (needs PostgreSQL; see the README).

- The API is **full async**: every handler and dependency is `async def`, the DB is `AsyncSession`, outbound HTTP is `httpx.AsyncClient`. Sync libraries or CPU work go through `anyio.to_thread.run_sync`. Never write a sync `def` endpoint, even though the FastAPI skill allows it.
- ORM is **SQLAlchemy 2 (`Mapped[]`) with separate Pydantic schemas, not SQLModel**. Do not convert models to SQLModel.
- Schema changes only through Alembic revisions; no raw SQL in `modules/` (the tenant filter only covers ORM queries).

## Claude Code plugins

`.claude/settings.json` registers the team plugins. On first open of this repo in Claude Code, trust the folder and accept the marketplace/plugin install prompt (or run `/plugin` to install manually):

- `mattpocock-skills@mattpocock`: idea → spec → tickets → implement flow (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, `/pr`).
- `ponytail@ponytail`: keeps implementations minimal (YAGNI, stdlib first) while still testing risky logic.
- `postgres-best-practices@supabase-agent-skills`: Postgres query, index and schema guidance (Supabase's official skill), for API models and migrations.
- FastAPI skill (official, via `uvx library-skills --claude` in `apps/api`): lives at `apps/api/.claude/skills/fastapi`, a relative symlink into `apps/api/.venv`. It loads when Claude works in `apps/api` (or via `/add-dir apps/api`) and only resolves after `uv sync` in `apps/api`.
