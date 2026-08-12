#!/usr/bin/env bash
# Invocation tests for pre-commit-check.sh. Builds throwaway git repos and asserts exit codes.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre-commit-check.sh"
pass=0
fail=0

# Run the hook inside a fresh temp repo seeded by $1 (a function), assert exit code $2.
run_case() {
  local name="$1" setup="$2" want="$3"
  local dir
  dir="$(mktemp -d)"
  set +e
  (
    cd "$dir"
    git init -q
    git config user.email t@t.t
    git config user.name t
    git checkout -q -b work
    # Copy the hook under test into the temp repo so its relative logic runs there.
    mkdir -p scripts/hooks
    cp "$HOOK" scripts/hooks/pre-commit-check.sh
    "$setup"
    bash scripts/hooks/pre-commit-check.sh >/dev/null 2>&1
  )
  local got=$?
  set -e
  if [ "$got" -eq "$want" ]; then
    echo "ok   $name (exit $got)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (want $want, got $got)"
    fail=$((fail + 1))
  fi
}

# Case A: change a file in a folder with a tracked README, README NOT staged -> block (exit 1).
setup_block() {
  mkdir -p pkg
  printf '# pkg\n' >pkg/README.md
  printf 'x\n' >pkg/thing.txt
  git add pkg/README.md pkg/thing.txt README.md CHANGELOG.md 2>/dev/null || true
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/README.md pkg/thing.txt
  git commit -q -m "seed"
  # Now stage a change to pkg/thing.txt WITHOUT restaging pkg/README.md.
  printf 'y\n' >>pkg/thing.txt
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt README.md CHANGELOG.md
}

# Case B: same change but README IS staged -> pass (exit 0).
setup_pass() {
  mkdir -p pkg
  printf '# pkg\n' >pkg/README.md
  printf 'x\n' >pkg/thing.txt
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/README.md pkg/thing.txt
  git commit -q -m "seed"
  printf 'y\n' >>pkg/thing.txt
  printf 'note\n' >>pkg/README.md
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt pkg/README.md README.md CHANGELOG.md
}

# Case C: folder has NO tracked README -> not gated -> pass (exit 0).
setup_no_readme() {
  mkdir -p pkg
  printf 'x\n' >pkg/thing.txt
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  git add README.md CHANGELOG.md pkg/thing.txt
  git commit -q -m "seed"
  printf 'y\n' >>pkg/thing.txt
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add pkg/thing.txt README.md CHANGELOG.md
}

run_case "blocks when folder README not restaged" setup_block 1
run_case "passes when folder README restaged" setup_pass 0
run_case "passes when folder has no README" setup_no_readme 0

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
