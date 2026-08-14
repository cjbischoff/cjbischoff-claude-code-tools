#!/usr/bin/env bash
# Enforce the repo's commit governance rules. See CLAUDE.md.
set -euo pipefail

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "main" ]; then
  echo "error: direct commits to main are not permitted." >&2
  echo "fix: create a branch named <type>/<short-kebab-description> and commit there." >&2
  exit 1
fi

staged=$(git diff --cached --name-only)
if [ -z "$staged" ]; then
  exit 0
fi

# Run grep on stdin; exit 1 (no match) yields empty output, any other exit
# status is a real failure and stops the hook instead of silently passing.
safe_grep() {
  local out rc=0
  out=$(grep "$@") || rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "error: scope detection failed (grep exit ${rc})." >&2
    exit 1
  fi
  printf '%s' "$out"
}

# Split staged files: plugin-internal vs repo-level (root README/CHANGELOG exempt).
nondoc=$(safe_grep -vxE 'README\.md|CHANGELOG\.md' <<<"$staged")
repo_level=$(safe_grep -vE '^plugins/[^/]+/' <<<"$nondoc")
plugin_names=$(safe_grep -oE '^plugins/[^/]+/' <<<"$nondoc" | sort -u | cut -d/ -f2)

if [ -n "$repo_level" ]; then
  if ! grep -qx 'README.md' <<<"$staged"; then
    echo "error: this commit changes repo-level files but does not update README.md." >&2
    echo "fix: update README.md in the same commit and stage it." >&2
    exit 1
  fi
  if ! grep -qx 'CHANGELOG.md' <<<"$staged"; then
    echo "error: this commit changes repo-level files but does not update CHANGELOG.md." >&2
    echo "fix: add a Common Changelog entry in the same commit and stage it." >&2
    exit 1
  fi
fi

while IFS= read -r name; do
  [ -z "$name" ] && continue
  cl="plugins/${name}/CHANGELOG.md"
  if ! grep -qx "$cl" <<<"$staged"; then
    echo "error: this commit changes plugins/${name}/ but does not update ${cl}." >&2
    echo "fix: add a Common Changelog entry to ${cl} and stage it." >&2
    exit 1
  fi
done <<<"$plugin_names"

# Changes inside a Directory Guide folder require that folder's README.md.
# plugins/ is excluded: the plugin-changelog loop above and the general
# immediate-folder loop below already gate it, per-plugin instead of one
# root plugins/README.md trigger for every change anywhere in the tree.
guide_dirs=(scripts docs)
for dir in "${guide_dirs[@]}"; do
  dir_files=$(safe_grep -E "^${dir}/" <<<"$staged")
  others=$(safe_grep -vx "${dir}/README.md" <<<"$dir_files")
  if [ -n "$others" ] && ! grep -qx "${dir}/README.md" <<<"$staged"; then
    echo "error: this commit changes files under ${dir}/ but does not update ${dir}/README.md." >&2
    echo "fix: update ${dir}/README.md in the same commit and stage it." >&2
    exit 1
  fi
done

# General rule: any staged file whose immediate folder has a tracked README.md
# requires that README.md to be staged too.
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # A plugin-root CHANGELOG.md is exempt: the plugin-changelog loop above
  # already gates it, and requiring the plugin's README.md too would make a
  # changelog-only plugin commit impossible.
  [[ "$f" =~ ^plugins/[^/]+/CHANGELOG\.md$ ]] && continue
  d=$(dirname "$f")
  [ "$d" = "." ] && continue
  readme="$d/README.md"
  [ "$f" = "$readme" ] && continue
  if git ls-files --error-unmatch "$readme" >/dev/null 2>&1; then
    if ! grep -qx "$readme" <<<"$staged"; then
      echo "error: this commit changes ${f} but does not update ${readme}." >&2
      echo "fix: update ${readme} in the same commit and stage it." >&2
      exit 1
    fi
  fi
done <<<"$staged"
