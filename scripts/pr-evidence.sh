#!/usr/bin/env bash

# Upload screenshots for a PR description as assets of the `pr-evidence`
# pre-release and print one Markdown image line per file. Release assets live
# outside git, so clones stay small. Re-uploading a file name replaces it.
#
#   scripts/pr-evidence.sh <pr-number> <image>...
#
# Assets are named pr-<n>-<file name>. Paste the printed lines into the PR body.

set -euo pipefail

OWNER="Movon-Product-House"
REPO="teamku"
TAG="pr-evidence"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <pr-number> <image>..." >&2
  exit 2
fi
pr="$1"
shift

if ! gh release view "$TAG" -R "$OWNER/$REPO" >/dev/null 2>&1; then
  gh release create "$TAG" -R "$OWNER/$REPO" --target main --prerelease --latest=false \
    --title "PR evidence" \
    --notes "Screenshots for PR descriptions, uploaded by scripts/pr-evidence.sh. Not a release." \
    >/dev/null
fi

# The asset name comes from the file name, so upload renamed copies.
staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
for file in "$@"; do
  name="pr-$pr-$(basename "$file")"
  cp "$file" "$staging/$name"
  gh release upload "$TAG" "$staging/$name" -R "$OWNER/$REPO" --clobber
  echo "![$(basename "${file%.*}")](https://github.com/$OWNER/$REPO/releases/download/$TAG/$name)"
done
