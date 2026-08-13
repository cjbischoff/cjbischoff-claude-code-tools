# .github/

GitHub-native security and automation for this marketplace. These files are
not shipped inside a plugin cache; they only run on GitHub.

**Naming convention:** workflows under `workflows/` as `<purpose>.yml`;
Dependabot config at `dependabot.yml`; CodeQL path filters under `codeql/`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user
review before merge.

## Contents

| Path | Purpose |
|------|---------|
| `workflows/dependency-review.yml` | GitHub Dependency review on pull requests |
| `dependabot.yml` | Weekly Dependabot version updates for Actions and pip |
| `codeql/codeql-config.yml` | CodeQL path exclusions (test fixtures, caches) |
