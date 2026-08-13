#!/usr/bin/env bash
# Invocation tests for commit-msg-check.sh.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/commit-msg-check.sh"
pass=0
fail=0

run_case() {
  local name="$1" body="$2" want="$3"
  local f
  f="$(mktemp)"
  printf '%s' "$body" >"$f"
  set +e
  bash "$HOOK" "$f" >/dev/null 2>&1
  local got=$?
  set -e
  if [ "$got" -eq "$want" ]; then
    echo "ok   $name (exit $got)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (want exit $want; got exit $got)"
    fail=$((fail + 1))
  fi
  rm -f "$f"
}

run_case "accepts clean conventional header" \
  $'chore(hooks): simplify the commit message check\n' \
  0

run_case "accepts a body after the header" \
  $'chore(hooks): simplify the commit message check\n\nBody.\n' \
  0

run_case "skips merge commits" \
  $'Merge pull request #1 from cjbischoff/topic\n' \
  0

run_case "rejects bad header" \
  $'not a conventional commit\n' \
  1

run_case "rejects a summary of 50 chars or more" \
  $'chore(hooks): summary padded well past the fifty character limit here\n' \
  1

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
