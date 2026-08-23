> Favor precision over recall: only raise a finding when the evidence in `build.gradle` under
> review is confident, and stay silent when the version catalog or CI resolution behavior is not
> visible in the diff. Adapted from open-code-review (Apache-2.0).

#### Optional Configuration Left Without Required Version
- A dependency declared with no version where no version catalog (`libs.versions.toml`) or
  platform BOM supplies one, causing resolution to fail or float to an arbitrary version
- An `optional`/`compileOnly` dependency relied upon by code that executes outside the optional
  boundary, at runtime rather than only compile time

Do not report in the following cases:
- The version number is not on a newly added line of code
- The version is centrally managed via a version catalog or platform BOM

#### Dynamic Version Resolution Race
- A dependency using a dynamic version range (`+`, `latest.release`) that can resolve to a
  different artifact on each build, non-deterministic across CI runs
- Two `configurations` resolving the same module to different versions with no explicit
  `resolutionStrategy.force`, left to Gradle's conflict resolution to decide

Do not report in the following cases:
- The dynamic range is already pinned via `resolutionStrategy`
- The range is intentional for a first-party snapshot-tracking module

#### Injection via Build Script Execution
- An `Exec` task or `doLast`/`doFirst` block interpolating an environment variable or project
  property sourced from untrusted CI input directly into a shell command
- A dependency or plugin resolved from an HTTP (non-HTTPS) repository URL, allowing substitution
  of the fetched artifact

Do not report in the following cases:
- The command uses fixed literal arguments with no interpolation
- The repository is a well-known trusted mirror already used elsewhere in the file

#### Snapshot and Unbounded Dependency Resource Risk
- A dependency or the project's own version carrying a snapshot qualifier (`-SNAPSHOT`) in a
  production/release build, pulling in a mutable, unreproducible artifact
- A repository block allowing snapshot resolution from a remote source with no pinned build
  identifier

Do not report in the following cases:
- The version number is not on a newly added line of code
- The module is explicitly local development/test-only and never released

#### Suppressed Build and Test Error Handling
- `ignoreFailures = true` on a `Test`, lint, or checkstyle task, hiding failing tests or
  violations from the build result
- A `doLast`/`doFirst` block swallowing an exception with an empty catch instead of failing the
  build

Do not report in the following cases:
- `ignoreFailures` is scoped to a documented flaky or integration-only test suite
- The setting is unchanged from the file's pre-existing baseline
