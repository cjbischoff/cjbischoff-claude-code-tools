#!/usr/bin/env bash
# Enforce Conventional Commits message format. See CLAUDE.md.
set -euo pipefail

msg_file="$1"

# Strip Cursor/agent attribution trailers before format checks.
# commit-msg hooks may rewrite the message file.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
grep -viE '^Co-authored-by: Cursor |^Co-authored-by:.*cursoragent@|^Made-with: Cursor|^Generated-by: Cursor|^Generated with Cursor' "$msg_file" \
  | awk 'BEGIN{b=0} /^$/{if(b) next; b=1; print; next} {b=0; print}' >"$tmp"
# Keep a single trailing newline.
python3 -c 'from pathlib import Path; import sys; p=Path(sys.argv[1]); p.write_text(p.read_text().rstrip()+"\n")' "$tmp"
mv "$tmp" "$msg_file"
trap - EXIT

header=$(head -n1 "$msg_file")

case "$header" in
Merge\ * | Revert\ *) exit 0 ;;
esac

regex='^(feat|fix|chore|docs|style|refactor|perf|test)(\([a-z0-9-]+\))?!?: [a-z]'
if ! grep -qE "$regex" <<<"$header"; then
  echo "error: commit header does not match Conventional Commits format." >&2
  echo "expected: <type>(<optional-scope>): <imperative summary, under 50 chars>" >&2
  echo "types: feat fix chore docs style refactor perf test" >&2
  echo "got: $header" >&2
  exit 1
fi

summary="${header#*: }"
if [ "${#summary}" -ge 50 ]; then
  echo "error: commit summary is ${#summary} chars; it must be under 50." >&2
  echo "got: $summary" >&2
  exit 1
fi
