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

## Claude Code plugins

`.claude/settings.json` registers the team plugins. On first open of this repo in Claude Code, trust the folder and accept the marketplace/plugin install prompt (or run `/plugin` to install manually):

- `mattpocock-skills@mattpocock`: idea → spec → tickets → implement flow (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/tdd`, `/code-review`, `/pr`).
- `ponytail@ponytail`: keeps implementations minimal (YAGNI, stdlib first) while still testing risky logic.
