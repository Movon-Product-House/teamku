# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). Older `gh`: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>` (database id, as in **Blocking** below). Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Siklus tiket (wajib setiap mengerjakan issue)

Dua engineer bekerja paralel; status issue adalah satu-satunya cara tahu siapa mengerjakan apa. GitHub dan agent **tidak** memperbarui status sendiri, kecuali yang ditandai _otomatis_.

Board: [Teamku Revamp v2](https://github.com/orgs/Movon-Product-House/projects/1), kolom Status `Todo → In Progress → In Review → Done`. Ubah status dengan `scripts/issue-status.sh <n> "<Status>"` (butuh scope `project`: `gh auth refresh -h github.com -s project`).

1. **Ambil**, sebelum menulis kode:
   - Cek `gh issue view <n> --json assignees`. Sudah ada assignee lain → jangan diambil, tanya user.
   - `gh issue edit <n> --add-assignee @me`
   - `scripts/issue-status.sh <n> "In Progress"`
   - `gh issue comment <n> --body "Mulai. Branch \`<branch>\`. Scope: <FE/BE/semua>."`
2. **Selama dikerjakan:**
   - Centang item checklist FE/BE di body issue begitu selesai (`gh issue edit <n> --body-file`), jangan menunggu PR.
   - Celah backend baru, blocker, atau keputusan scope → komentar di issue, bukan hanya di chat.
3. **PR:** branch `feat/<n>-<slug>`. Satu issue boleh beberapa PR (mis. per layar): PR terakhir memakai `Closes #<n>`, PR sebelumnya `Refs #<n>`. Body PR menyebut item checklist yang selesai dan yang sengaja ditunda; item yang ditunda dijadikan issue baru. Setelah PR dibuka: `scripts/issue-status.sh <n> "In Review"`.
4. **Selesai:** _otomatis_. PR dengan `Closes #<n>` menutup issue saat merge, dan board memindahkannya ke Done.
5. **Berhenti di tengah** (sesi habis, pindah tugas): komentar status singkat (sudah apa, sisa apa, branch), biarkan assignee. Melepas tiket: `gh issue edit <n> --remove-assignee @me` + `scripts/issue-status.sh <n> Todo`.

Sebelum melaporkan pekerjaan selesai ke user, cek ulang: assignee, status board, checklist, dan `Closes`/`Refs` di PR sudah sesuai.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (see **Make an issue a sub-issue of a parent**). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, the canonical, UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
