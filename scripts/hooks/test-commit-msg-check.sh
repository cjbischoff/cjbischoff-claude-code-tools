#!/usr/bin/env bash
# Invocation tests for commit-msg-check.sh.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/commit-msg-check.sh"
pass=0
fail=0

run_case() {
  local name="$1" body="$2" want="$3" expect_trailer="$4"
  local f
  f="$(mktemp)"
  printf '%s' "$body" >"$f"
  set +e
  bash "$HOOK" "$f" >/dev/null 2>&1
  local got=$?
  set -e
  local has_trailer=0
  grep -qi 'cursoragent@' "$f" && has_trailer=1
  if [ "$got" -eq "$want" ] && [ "$has_trailer" -eq "$expect_trailer" ]; then
    echo "ok   $name (exit $got, trailer=$has_trailer)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (want exit $want trailer=$expect_trailer; got exit $got trailer=$has_trailer)"
    fail=$((fail + 1))
  fi
  rm -f "$f"
}

run_case "strips Cursor trailer" \
  $'chore(cursor): stop agent commit attribution\n\nBody.\n\nCo-authored-by: Cursor <cursoragent@cursor.com>\n' \
  0 0

run_case "accepts clean conventional header" \
  $'chore(cursor): stop agent commit attribution\n' \
  0 0

run_case "rejects bad header" \
  $'not a conventional commit\n' \
  1 0

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
