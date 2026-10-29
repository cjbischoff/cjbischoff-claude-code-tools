# templates/

Files that `/readme-keeper:check --install-ci` copies into a target repository.

| File | Installed as | Purpose |
|------|--------------|---------|
| `readme-check.yml` | `.github/workflows/readme-check.yml` | GitHub Actions workflow. On a pull request that touches a README, it runs `python3 .github/scripts/readme_check.py --all` offline. |

## Install

`/readme-keeper:check --install-ci` shows a diff that adds two files to the target repo:

1. `skills/readme-keeper/scripts/check.py` becomes `.github/scripts/readme_check.py`.
2. `templates/readme-check.yml` becomes `.github/workflows/readme-check.yml`.

The user approves the diff before the command writes anything. The installed script is a copy pinned to the plugin version at install time. It runs without the plugin. To update it, run `--install-ci` again.

## Maintenance

The workflow pins `actions/checkout` to a commit SHA (currently v7.0.1). Refresh the pin whenever you update this template:

```bash
tag=$(gh api repos/actions/checkout/releases/latest --jq .tag_name)
gh api repos/actions/checkout/git/ref/tags/"$tag" --jq .object.sha
```

If the second command returns a tag object instead of a commit, dereference it before you pin. Run `actionlint` on the template after every change.
