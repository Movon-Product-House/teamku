#!/usr/bin/env bash

# Set the Status of an issue on the "Teamku Revamp v2" GitHub Project board.
# Adds the issue to the board first if it is not there yet.
#
#   scripts/issue-status.sh <issue-number> "<Todo|In Progress|In Review|Done>"
#
# Needs the `project` scope: gh auth refresh -h github.com -s project

set -euo pipefail

OWNER="Movon-Product-House"
REPO="teamku"
PROJECT=1

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <issue-number> \"<Todo|In Progress|In Review|Done>\"" >&2
  exit 2
fi
issue="$1"
status="$2"

project_id=$(gh project view "$PROJECT" --owner "$OWNER" --format json -q .id)
field=$(gh project field-list "$PROJECT" --owner "$OWNER" --format json -q '.fields[] | select(.name == "Status")')
field_id=$(jq -r .id <<<"$field")
option_id=$(jq -r --arg s "$status" '.options[] | select(.name == $s) | .id' <<<"$field")
if [[ -z "$option_id" ]]; then
  echo "Status tidak dikenal: \"$status\". Pilihan: $(jq -r '[.options[].name] | join(", ")' <<<"$field")" >&2
  exit 2
fi

item_id=$(gh api graphql -F n="$issue" -f query="
  query(\$n: Int!) { repository(owner: \"$OWNER\", name: \"$REPO\") { issue(number: \$n) {
    projectItems(first: 20) { nodes { id project { number } } } } } }" \
  --jq ".data.repository.issue.projectItems.nodes[] | select(.project.number == $PROJECT) | .id")
if [[ -z "$item_id" ]]; then
  item_id=$(gh project item-add "$PROJECT" --owner "$OWNER" \
    --url "https://github.com/$OWNER/$REPO/issues/$issue" --format json -q .id)
fi

gh project item-edit --id "$item_id" --project-id "$project_id" \
  --field-id "$field_id" --single-select-option-id "$option_id" >/dev/null
echo "#$issue → $status"
