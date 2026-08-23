> Favor precision over recall: only raise a finding when the evidence in `package.json` under
> review is confident, and stay silent when the monorepo/workspace context is not visible in the
> diff. Adapted from open-code-review (Apache-2.0).

#### Optional and Peer Dependency Declaration Gaps
- A tool invoked in `scripts` (eslint, jest, prettier, webpack, tsc) that is not declared in
  `dependencies`/`devDependencies`, relying on a global install CI will not have
- A `peerDependencies` entry with no `peerDependenciesMeta.optional` marking, where the feature
  using it is genuinely optional at runtime

Do not report in the following cases:
- The tool is provided by a parent workspace's `devDependencies` in a monorepo
- The script is a documented manual/local-only command, never run in CI

#### Dependency Version Resolution Race Across Declarations
- The same package declared in both `dependencies` and `devDependencies` with different version
  ranges, resolving inconsistently depending on install tool and order
- Two dependencies declaring conflicting peer-version ranges for the same transitive package

Do not report in the following cases:
- The versions in both sections match exactly
- The conflict is already resolved via `overrides`/`resolutions`

#### Injection via Lifecycle Scripts
- A `scripts` entry (`preinstall`, `postinstall`, `prepare`) that interpolates an environment
  variable or `npm_config_*` value directly into a shell command
- A `scripts` entry that fetches and executes a remote URL (`curl | sh` pattern) instead of using
  a pinned local dependency

Do not report in the following cases:
- The script uses a fixed literal command with no interpolation
- The environment value is already validated/escaped by the invoked tool itself

#### Unbounded Version Ranges and Dependency Resource Exposure
- A dependency pinned to `latest` or `*` instead of a specific or compatible version, letting an
  unreviewed future release install without warning
- A `git`/URL dependency with no commit pin, letting the remote source change what code installs

Do not report in the following cases:
- The version number is not on a newly added line in the diff
- The range is a documented compatible range (`^`/`~`) consistent with sibling entries

#### Swallowed Errors in Install and Build Failures
- A `scripts` entry suffixed with `|| true` or `; exit 0`, hiding a build or test failure from CI
- `engines` declared but not enforced (no `engine-strict`), silently allowing an incompatible
  Node/npm version to install

Do not report in the following cases:
- The suppression is on a documented best-effort or cleanup-only step
- The failure is already caught by a separate, required CI check
