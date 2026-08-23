> Favor precision over recall: report only Nix issues likely to break evaluation,
> reproducibility, build isolation, security, or deployment behavior. Adapted from open-code-review (Apache-2.0).

#### Missing Attributes and Null-or-Undefined References
- Referencing `self`, `super`, `pkgs`, `config`, or function arguments not in scope
  for the changed expression, which fails evaluation
- `inherit` statements that reference missing names, or inherit from an attrset that
  cannot contain the requested attribute
- An option used before declaration, or with a default whose type does not match the
  declared `types.*`

Do not report in the following cases:
- The name is bound by a `with` or module argument visible earlier in the same file
- The attribute is genuinely optional and the consuming code already guards for its
  absence

#### Attribute-Set Override Ordering and Evaluation Races
Nix evaluation is lazy and single-threaded, but overlay/override ordering creates an
analogous hazard:
- Overlay functions with argument order or names swapped (`final`/`prev`,
  `self`/`super`), causing packages to be pulled from the wrong package set
- Duplicate attribute definitions in the same attrset, or an override that
  unintentionally replaces a previously defined value in the changed scope

Do not report in the following cases:
- The overlay argument names already match the convention used elsewhere in the file
- No evidence an override actually shadows a value used later

#### Injection via Unpinned Sources and Secret Exposure
- Fetchers (`fetchTarball`, `fetchGit`, `fetchurl`, `fetchFromGitHub`,
  `builtins.fetch*`) without a fixed revision and hash when the source affects a
  package, module, or deployment output
- Secrets or credentials embedded directly in module defaults, environment
  variables, scripts, or generated config instead of coming from secret management

Do not report in the following cases:
- The fetch is already pinned to a revision and hash
- The value is a non-secret default clearly documented as safe to commit

#### Resource Isolation: Sandbox Escapes and Undeclared Build Inputs
- Derivations using undeclared build tools or runtime dependencies instead of
  adding them to `nativeBuildInputs`, `buildInputs`, or `propagatedBuildInputs`
- Hardcoded host paths, user home paths, or `/usr/bin` tools inside derivations that
  should build inside the Nix sandbox

Do not report in the following cases:
- The tool is already declared in the appropriate `*Inputs` list
- The path is a Nix store path produced by an input, not a host path

#### Swallowed Migration Errors in Modules and Phases
- A phase override that drops required default behavior without reintroducing it
  (e.g. replacing `installPhase` without installing outputs into `$out`)
- A renamed NixOS/Home Manager option with no compatibility alias or migration path,
  silently dropping the old configuration on upgrade

Do not report in the following cases:
- The phase override already calls through to the default behavior it replaces
- The rename includes a documented alias or migration note in the same diff
