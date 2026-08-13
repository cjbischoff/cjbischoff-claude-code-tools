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

# Any commit that changes more than the doc files must update both doc files.
nondoc=$(grep -vxE 'README\.md|CHANGELOG\.md' <<<"$staged" || true)
if [ -n "$nondoc" ]; then
  if ! grep -qx 'README.md' <<<"$staged"; then
    echo "error: this commit changes tracked files but does not update README.md." >&2
    echo "fix: update README.md in the same commit and stage it." >&2
    exit 1
  fi
  if ! grep -qx 'CHANGELOG.md' <<<"$staged"; then
    echo "error: this commit changes tracked files but does not update CHANGELOG.md." >&2
    echo "fix: add a Common Changelog entry in the same commit and stage it." >&2
    exit 1
  fi
fi

# Changes inside a Directory Guide folder require that folder's README.md.
guide_dirs=(plugins scripts docs)
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
