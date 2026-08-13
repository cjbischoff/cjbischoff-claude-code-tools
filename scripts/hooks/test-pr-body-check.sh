#!/usr/bin/env bash
# Invocation tests for pr-body-check.sh.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pr-body-check.sh"
pass=0
fail=0

report() {
  local name="$1" want="$2" got="$3"
  if [ "$got" -eq "$want" ]; then
    echo "ok   $name (exit $got)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (want exit $want; got exit $got)"
    fail=$((fail + 1))
  fi
}

run_stdin() {
  local name="$1" body="$2" want="$3" got=0
  printf '%s' "$body" | bash "$HOOK" >/dev/null 2>&1 || got=$?
  report "$name" "$want" "$got"
}

run_file() {
  local name="$1" body="$2" want="$3" got=0 f
  f="$(mktemp)"
  printf '%s' "$body" >"$f"
  bash "$HOOK" "$f" >/dev/null 2>&1 || got=$?
  rm -f "$f"
  report "$name" "$want" "$got"
}

run_stdin "rejects the Made with Cursor footer" \
  $'## Summary\n\n- Do a thing.\n\nMade with [Cursor](https://cursor.com)\n' \
  1

run_stdin "rejects a Cursor co-author trailer" \
  $'## Summary\n\nCo-authored-by: Cursor <cursoragent@cursor.com>\n' \
  1

run_stdin "rejects a bare cursoragent address" \
  $'## Summary\n\nAsk cursoragent@cursor.com about it.\n' \
  1

run_stdin "rejects a Generated with Claude footer" \
  $'## Summary\n\nGenerated with Claude\n' \
  1

run_stdin "accepts a clean body" \
  $'## Summary\n\n- Do a thing.\n\n## Test plan\n\n- [ ] Check it.\n' \
  0

run_stdin "accepts prose naming Cursor without attribution" \
  $'## Summary\n\n- Explain how Cursor appends the footer, and how the check strips it.\n' \
  0

run_stdin "accepts an empty body" "" 0

run_file "rejects attribution read from a file" \
  $'## Summary\n\nMade with [Cursor](https://cursor.com)\n' \
  1

run_file "accepts a clean body read from a file" \
  $'## Summary\n\n- Do a thing.\n' \
  0

got=0
bash "$HOOK" /nonexistent/pr-body.md >/dev/null 2>&1 || got=$?
report "fails closed on an unreadable path" 2 "$got"

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
