---
description: Check a README against the repo with deterministic rules, read-only
argument-hint: [path | --all] [--exclude GLOB] [--links] [--prose] [--strict] [--install-ci]
---
Use the `readme-keeper` skill in check mode on: $ARGUMENTS

Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/readme-keeper/scripts/check.py" <arguments>` and report its findings. Omit `--install-ci` from the arguments, because `check.py` does not accept it. Do not change any file in check mode.

If `--install-ci` is present, follow the CI template section of the skill. Show a diff that copies `${CLAUDE_PLUGIN_ROOT}/skills/readme-keeper/scripts/check.py` to `.github/scripts/readme_check.py` and `${CLAUDE_PLUGIN_ROOT}/templates/readme-check.yml` to `.github/workflows/readme-check.yml`. Write the files only after the user approves the diff.

Never commit. Never run code from the target repo.
