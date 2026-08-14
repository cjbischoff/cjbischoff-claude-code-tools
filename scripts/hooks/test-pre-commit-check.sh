#!/usr/bin/env bash
# Invocation tests for pre-commit-check.sh. Builds throwaway git repos and asserts exit codes.
set -euo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre-commit-check.sh"
pass=0
fail=0
tmpdirs=()
cleanup() {
  [ ${#tmpdirs[@]} -gt 0 ] && rm -rf "${tmpdirs[@]}"
}
trap cleanup EXIT

# Run the hook inside a fresh temp repo seeded by $1 (a function), assert exit code $2.
run_case() {
  local name="$1" setup="$2" want="$3"
  local dir
  dir="$(mktemp -d)"
  tmpdirs+=("$dir")
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

# Case D: plugin-only change without the plugin's own CHANGELOG.md -> block (exit 1).
# plugins/README.md is tracked but NOT staged here: this proves plugin-internal
# commits are exempt from the old blanket plugins/README.md trigger.
setup_plugin_no_changelog() {
  mkdir -p plugins/demo
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf '# plugins\n' >plugins/README.md
  printf 'x\n' >plugins/demo/CHANGELOG.md
  printf 'x\n' >plugins/demo/file.txt
  git add README.md CHANGELOG.md plugins/README.md plugins/demo/CHANGELOG.md plugins/demo/file.txt
  git commit -q -m "seed"
  printf 'y\n' >>plugins/demo/file.txt
  git add plugins/demo/file.txt
}

# Case E: plugin-only change with the plugin's own CHANGELOG.md staged, no
# plugins/README.md, no root docs -> pass (exit 0). This is the exemption:
# the old hook demanded root README/CHANGELOG here; the new one does not.
setup_plugin_with_changelog() {
  mkdir -p plugins/demo
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf '# plugins\n' >plugins/README.md
  printf 'x\n' >plugins/demo/CHANGELOG.md
  printf 'x\n' >plugins/demo/file.txt
  git add README.md CHANGELOG.md plugins/README.md plugins/demo/CHANGELOG.md plugins/demo/file.txt
  git commit -q -m "seed"
  printf 'y\n' >>plugins/demo/file.txt
  printf 'note\n' >>plugins/demo/CHANGELOG.md
  git add plugins/demo/file.txt plugins/demo/CHANGELOG.md
}

# Case H: a file directly in plugins/demo/ with a tracked plugins/demo/README.md,
# that README NOT restaged -> still blocked (exit 1). Proves the immediate-folder
# loop still gates inside a plugin tree even though guide_dirs no longer does.
setup_plugin_folder_readme_not_staged() {
  mkdir -p plugins/demo
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf '# plugins\n' >plugins/README.md
  printf '# demo\n' >plugins/demo/README.md
  printf 'x\n' >plugins/demo/CHANGELOG.md
  printf 'x\n' >plugins/demo/file.txt
  git add README.md CHANGELOG.md plugins/README.md plugins/demo/README.md \
    plugins/demo/CHANGELOG.md plugins/demo/file.txt
  git commit -q -m "seed"
  printf 'y\n' >>plugins/demo/file.txt
  printf 'note\n' >>plugins/demo/CHANGELOG.md
  git add plugins/demo/file.txt plugins/demo/CHANGELOG.md
}

# Case F: repo-level change without root README/CHANGELOG staged -> block (exit 1).
setup_repo_level_no_docs() {
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf 'x\n' >file-at-root.txt
  git add README.md CHANGELOG.md file-at-root.txt
  git commit -q -m "seed"
  printf 'y\n' >>file-at-root.txt
  git add file-at-root.txt
}

# Case G: repo-level change with root README/CHANGELOG staged -> pass (exit 0).
setup_repo_level_with_docs() {
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf 'x\n' >file-at-root.txt
  git add README.md CHANGELOG.md file-at-root.txt
  git commit -q -m "seed"
  printf 'y\n' >>file-at-root.txt
  printf 'changed\n' >>README.md
  printf 'changed\n' >>CHANGELOG.md
  git add file-at-root.txt README.md CHANGELOG.md
}

run_case "plugin change without plugin changelog" setup_plugin_no_changelog 1
run_case "plugin change with plugin changelog" setup_plugin_with_changelog 0
run_case "repo-level change without root docs" setup_repo_level_no_docs 1
run_case "repo-level change with root docs" setup_repo_level_with_docs 0
run_case "blocks when plugin folder README not restaged" setup_plugin_folder_readme_not_staged 1

# Case I: plugin CHANGELOG.md is a TRACKED sibling of a TRACKED plugin
# README.md, and the commit stages only the changelog edit -> pass (exit 0).
# Proves the changelog exemption from the general immediate-folder README
# loop, in the real-repo shape where plugins/demo/README.md also exists.
setup_plugin_changelog_only_readme_tracked() {
  mkdir -p plugins/demo
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf '# plugins\n' >plugins/README.md
  printf '# demo\n' >plugins/demo/README.md
  printf 'x\n' >plugins/demo/CHANGELOG.md
  printf 'x\n' >plugins/demo/somefile
  git add README.md CHANGELOG.md plugins/README.md plugins/demo/README.md \
    plugins/demo/CHANGELOG.md plugins/demo/somefile
  git commit -q -m "seed"
  printf 'note\n' >>plugins/demo/CHANGELOG.md
  git add plugins/demo/CHANGELOG.md
}

# Case J: same tracked fixture as Case I, but the commit also touches
# plugins/demo/somefile without restaging plugins/demo/README.md -> still
# blocked (exit 1). The changelog exemption covers only the changelog itself,
# not its siblings.
setup_plugin_changelog_and_file_no_readme() {
  mkdir -p plugins/demo
  printf '# r\n' >README.md
  printf '# c\n' >CHANGELOG.md
  printf '# plugins\n' >plugins/README.md
  printf '# demo\n' >plugins/demo/README.md
  printf 'x\n' >plugins/demo/CHANGELOG.md
  printf 'x\n' >plugins/demo/somefile
  git add README.md CHANGELOG.md plugins/README.md plugins/demo/README.md \
    plugins/demo/CHANGELOG.md plugins/demo/somefile
  git commit -q -m "seed"
  printf 'note\n' >>plugins/demo/CHANGELOG.md
  printf 'y\n' >>plugins/demo/somefile
  git add plugins/demo/CHANGELOG.md plugins/demo/somefile
}

run_case "plugin changelog-only commit passes with plugin README tracked" \
  setup_plugin_changelog_only_readme_tracked 0
run_case "plugin changelog plus file still blocks without plugin README" \
  setup_plugin_changelog_and_file_no_readme 1

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
