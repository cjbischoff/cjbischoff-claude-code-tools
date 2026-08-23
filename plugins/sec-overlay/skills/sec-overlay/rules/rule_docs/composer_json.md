> Favor precision over recall: only raise a finding when the evidence in `composer.json` under
> review is confident, and stay silent when CI, deployment configuration, or sibling manifests are
> not visible in the diff. Adapted from open-code-review (Apache-2.0).

#### Missing Required and Optional Platform Extension Declarations
- A newly used package or mandatory PHP extension absent from `require`, causing a clean
  production install to fail on the missing `ext-*` requirement
- A required native extension made mandatory even though the code has a working optional fallback

Do not report in the following cases:
- The extension is bundled with the deployment platform's base image, confirmed elsewhere in the
  diff (Dockerfile, CI config)
- The fallback path is untested and clearly unmaintained dead code

#### Autoload Path Resolution and Namespace Synchronization
- Overlapping PSR-4 namespace prefixes resolving the wrong class depending on autoloader scan order
- Classmap, exclusion, or `files` entries left stale after directories are moved or renamed,
  pointing at a path that no longer resolves

Do not report in the following cases:
- The overlap is a documented, intentional subset override
- The staleness is already caught by a CI autoload-validation step

#### Injection via Lifecycle Scripts and Plugin Execution
- A lifecycle script interpolating an untrusted environment value into a shell command, or running
  a destructive command during install/update
- A newly required Composer plugin with no intentional `config.allow-plugins` decision, or a
  wildcard/broad authorization permitting unexpected code execution during install

Do not report in the following cases:
- The script uses fixed literal commands with no interpolation
- The script or plugin merely executes code with no concrete unsafe command or trust-boundary
  change established — do not flag execution alone

#### Wildcard Constraints and Insecure Source Resource Exposure
- A wildcard constraint (`*`), an unconstrained `dev-*` branch, or a mutable VCS reference
  introduced with no committed, current lock file where the application build requires
  reproducibility
- `secure-http` disabled, a plaintext repository URL, or embedded credentials in a repository
  source

Do not report in the following cases:
- The constraint is a compatible version range (`^`/`~`) in a reusable library where consumers
  resolve their own dependencies
- The wildcard or insecure source already existed before this diff

#### Silenced Error Handling and Weakened Stability
- `minimum-stability` weakened to admit unrelated development packages into resolution, especially
  without `prefer-stable`
- An incorrect `replace`, `provide`, or `conflict` declaration that makes Composer silently omit a
  required implementation or accept an incompatible package

Do not report in the following cases:
- A narrowly constrained development dependency is already documented as intentional
- The declaration is unchanged from the file's pre-existing baseline
