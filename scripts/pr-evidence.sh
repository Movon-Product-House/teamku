#!/usr/bin/env bash

# Upload screenshots for a PR description to the `pr-evidence` branch and print
# one Markdown image line per file. The branch only holds images, so the PR diff
# and main stay free of them. Re-uploading a file name replaces it.
#
#   scripts/pr-evidence.sh <pr-number> <image>...
#
# Files land at pr-<n>/<file name>. Paste the printed lines into the PR body.

set -euo pipefail

OWNER="Movon-Product-House"
REPO="teamku"
BRANCH="pr-evidence"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <pr-number> <image>..." >&2
  exit 2
fi
pr="$1"
shift

if ! gh api "repos/$OWNER/$REPO/branches/$BRANCH" >/dev/null 2>&1; then
  # Orphan branch: a single README commit with no history from main.
  tree=$(gh api -X POST "repos/$OWNER/$REPO/git/trees" \
    -f 'tree[][path]=README.md' -f 'tree[][mode]=100644' -f 'tree[][type]=blob' \
    -f 'tree[][content]=Screenshots for PR descriptions, uploaded by scripts/pr-evidence.sh.' \
    -q .sha)
  commit=$(gh api -X POST "repos/$OWNER/$REPO/git/commits" \
    -f message="chore: start pr-evidence branch" -f "tree=$tree" -q .sha)
  gh api -X POST "repos/$OWNER/$REPO/git/refs" \
    -f "ref=refs/heads/$BRANCH" -f "sha=$commit" >/dev/null
fi

for file in "$@"; do
  path="pr-$pr/$(basename "$file")"
  # On 404 gh prints the error body to stdout, so keep the output only on success.
  sha=$(gh api "repos/$OWNER/$REPO/contents/$path?ref=$BRANCH" -q .sha 2>/dev/null) || sha=""
  # Body goes through stdin: base64 of a screenshot is too long for an argument.
  {
    printf '{"message":"evidence: PR #%s %s","branch":"%s",' "$pr" "$(basename "$file")" "$BRANCH"
    [[ -n "$sha" ]] && printf '"sha":"%s",' "$sha"
    printf '"content":"'
    base64 <"$file" | tr -d '\n'
    printf '"}'
  } | gh api -X PUT "repos/$OWNER/$REPO/contents/$path" --input - >/dev/null
  echo "![$(basename "${file%.*}")](https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH/$path)"
done
