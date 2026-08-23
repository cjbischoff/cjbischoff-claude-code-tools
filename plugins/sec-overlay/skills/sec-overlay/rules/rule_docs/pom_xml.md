> Favor precision over recall: only raise a finding when the evidence in `pom.xml` under review is
> confident, and stay silent when the parent POM or dependency-management hierarchy is not visible
> in the diff. Adapted from open-code-review (Apache-2.0).

#### Optional Dependency Scope and Version Omission
- A `<dependency>` with no `<version>` where no parent POM or `<dependencyManagement>` entry
  supplies one, causing the build to fail at resolution rather than at code level
- An `<optional>true</optional>` dependency that non-optional code in the same module relies on

Do not report in the following cases:
- The version is omitted because it is managed in the parent POM
- The version number is not on a newly added line of code

#### Dependency Resolution Ordering Race
- Two `<dependency>` entries for the same artifact with different versions and no explicit
  `<dependencyManagement>` pin, resolving to whichever Maven's nearest-wins algorithm picks
  depending on the declaration graph
- `<repositories>` entries in conflicting order that can resolve the same artifact from different
  sources depending on network availability

Do not report in the following cases:
- The conflict is already resolved via an explicit `<dependencyManagement>` entry
- Both entries pin the identical version

#### Injection via Plugin Execution Configuration
- A plugin (`exec-maven-plugin`, `antrun`) configured to run a shell command built by interpolating
  a property sourced from untrusted input (PR title, branch name, environment variable) without
  escaping
- A `<repository>` URL using plaintext HTTP instead of HTTPS, letting a network attacker substitute
  the resolved artifact

Do not report in the following cases:
- The command uses fixed literal arguments with no interpolation
- The repository is a well-known trusted mirror already used elsewhere in the file

#### Snapshot and Unbounded Version Resource Risk
- A dependency or the project's own `<version>` carrying the `-SNAPSHOT` qualifier in a
  production/release build, pulling in a mutable, unreproducible artifact
- `<repositories>` allowing snapshot resolution from a remote repo with no pinned build number

Do not report in the following cases:
- The version number is not on a newly added line of code
- The module is explicitly local development/test-only and never released

#### Suppressed Build and Test Error Handling
- `<testFailureIgnore>true</testFailureIgnore>`, `skipTests`, or `maven.test.skip` set to `true`,
  hiding failing tests from the build result
- A plugin execution with `failOnError`/`failOnWarning` disabled where sibling executions in the
  same file leave it enabled

Do not report in the following cases:
- The skip flag is scoped to a documented flaky or integration-only test suite
- The setting is unchanged from the file's pre-existing baseline
