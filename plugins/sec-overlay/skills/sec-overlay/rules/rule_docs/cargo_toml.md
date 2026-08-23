> Favor precision over recall: only raise a finding when the evidence in `Cargo.toml` under review
> is confident, and stay silent when the crate's publish status or workspace layout is not visible
> in the diff. Adapted from open-code-review (Apache-2.0).

#### Missing Optional Feature Boundaries
- An optional dependency exposed as a public feature name that leaks the internal dependency name
  instead of an intentional feature name
- Default features left large enough to enable a heavy optional integration without a clear reason
  stated in the diff, when a library should keep defaults small

Do not report in the following cases:
- The dependency is intentionally always-required, not optional
- The feature name matching the dependency name is the crate's established convention elsewhere
  in the file

#### Feature Resolver Synchronization Across Workspace Crates
- A workspace omitting `resolver = "2"` (or using resolver v1) where multiple crates' feature
  unification can silently enable a feature in a build profile that should not have it
- A feature that disables behavior in a dependent crate instead of only adding to it, breaking the
  "features are additive" invariant once combined with a sibling crate's features

Do not report in the following cases:
- The workspace already declares `resolver = "2"` or newer
- The feature is purely additive per its own doc comment or usage in the diff

#### Injection via Build Scripts
- `build.rs` or a `[build-dependencies]` script interpolating an environment variable into a shell
  command executed during the build
- A `git` dependency URL or patch source that a build script fetches and executes with no pin or
  checksum verification

Do not report in the following cases:
- The build script uses fixed literal commands with no interpolation
- The git dependency already pins a `rev`

#### Unpinned Dependency Sourcing and Packaging Resource Exposure
- A wildcard dependency version (`*`) instead of an explicit compatible version requirement
- An unpinned `git` dependency in a production crate with no `rev`/`tag` and no documented
  reproducibility policy
- Missing `include`/`exclude` settings risking packaging of credentials, local paths, or large
  binary assets into the published crate

Do not report in the following cases:
- The version number is not on a newly added line of code
- The crate declares `publish = false` and is never distributed

#### Missing Metadata Hiding Release Errors
- A published crate missing `license`/`license-file`, `repository`, or `description`, causing a
  registry publish to fail or misleading consumers about provenance
- `rust-version` (MSRV) omitted in a repository with a stated MSRV policy, letting an incompatible
  dependency bump silently break older toolchains until a downstream build fails

Do not report in the following cases:
- The crate declares `publish = false`
- No MSRV policy is documented anywhere in the repository
