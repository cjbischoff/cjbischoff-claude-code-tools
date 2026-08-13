#!/usr/bin/env bash
# Reject agent attribution in a pull request body. See CLAUDE.md.
set -euo pipefail

# Reads the body from a file argument, or from stdin when given "-" or nothing.
src="${1:--}"
if [ "$src" = "-" ]; then
  body=$(cat)
elif [ -r "$src" ]; then
  body=$(cat -- "$src")
else
  echo "error: cannot read pull request body from '${src}'." >&2
  exit 2
fi

named='\[?(Cursor|Claude)'
pattern="Co-authored-by:[[:space:]]*${named}|cursoragent@|(Made|Generated)[[:space:]]+(with|by)[[:space:]]+${named}"

if hits=$(grep -inE "$pattern" <<<"$body"); then
  echo "error: pull request body carries agent attribution." >&2
  echo "$hits" >&2
  echo "fix: remove the attribution footer, then run 'gh pr edit <n> --body-file -'." >&2
  exit 1
fi

echo "ok: no agent attribution in the pull request body."
