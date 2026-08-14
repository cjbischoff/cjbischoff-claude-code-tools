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

# Split staged files: plugin-internal vs repo-level (root README/CHANGELOG exempt).
nondoc=$(grep -vxE 'README\.md|CHANGELOG\.md' <<<"$staged" || true)
repo_level=$(grep -vE '^plugins/[^/]+/' <<<"$nondoc" || true)
plugin_names=$(grep -oE '^plugins/[^/]+/' <<<"$nondoc" | sort -u | cut -d/ -f2 || true)

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

for name in $plugin_names; do
  cl="plugins/${name}/CHANGELOG.md"
  if ! grep -qx "$cl" <<<"$staged"; then
    echo "error: this commit changes plugins/${name}/ but does not update ${cl}." >&2
    echo "fix: add a Common Changelog entry to ${cl} and stage it." >&2
    exit 1
  fi
done

# Changes inside a Directory Guide folder require that folder's README.md.
# plugins/ is excluded: the plugin-changelog loop above and the general
# immediate-folder loop below already gate it, per-plugin instead of one
# root plugins/README.md trigger for every change anywhere in the tree.
guide_dirs=(scripts docs)
for dir in "${guide_dirs[@]}"; do
  others=$(grep -E "^${dir}/" <<<"$staged" | grep -vx "${dir}/README.md" || true)
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
