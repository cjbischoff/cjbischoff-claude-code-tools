> Favor precision over recall: only raise a finding when the evidence in the HCL under review is
> confident, and stay silent when provider behavior, cloud account state, or remote state content
> is not observable in the diff. Adapted from open-code-review (Apache-2.0).

#### Missing Required Values and Optional Field Handling
- A required `variable` with no default and no validation block, consumed downstream where an
  absent value would break the resource graph
- A `variable` block that clearly holds a credential (name/description implies password, token,
  key, secret) missing `sensitive = true`, or a derived output of that value missing `sensitive`
- An `output` exposing a value that traces back to a sensitive input without `sensitive = true`

Do not report in the following cases:
- The value has a documented default, or the consumer already null-checks via `try()`/`coalesce()`
- The variable is genuinely optional and downstream code visibly tolerates its absence

#### Provider Concurrency and State Race Conditions
- Removing or weakening `lifecycle { prevent_destroy = true }` on a stateful resource (database,
  persistent volume, KMS key) without an explanation visible in the diff
- Duplicate resource/data-source labels within the same module, which resolve non-deterministically
  or fail `terraform validate` depending on apply ordering

Do not report in the following cases:
- Sibling resources of the same kind in the diff also lack lifecycle protection (pre-existing
  inconsistency, not a new regression)
- The issue is formatting/whitespace that `terraform fmt` would silently fix

#### Template and Injection Risks
- Untrusted input (a variable sourced from an external system, PR-controlled data, or unsanitized
  user input) interpolated into `templatefile()`, `user_data`, or a `local-exec`/`remote-exec`
  provisioner command without escaping, enabling command injection on the executing host
- A provisioner command built by string concatenation of variable values instead of using the
  provisioner's argument list or a vetted template function

Do not report in the following cases:
- The interpolated value is a literal constant or a value fixed by the module's own configuration
- The template input is already sanitized/validated by a function visible earlier in the diff

#### Overly Permissive Access and Resource Exposure
- A security group/firewall/network ACL rule with an unrestricted source (`0.0.0.0/0`, `::/0`, or
  `"*"`) on a sensitive port (SSH/22, RDP/3389, database ports) or on all ports
- An IAM policy, role, or resource policy granting a wildcard action (`"Action": "*"`) or wildcard
  resource (`"Resource": "*"`) instead of a scoped permission set
- Public read/write ACLs or public access settings enabled on a storage resource with no clear
  public-content purpose stated in the diff

Do not report in the following cases:
- The rule is explicitly scoped and the surrounding names/comments state an intentional public
  endpoint (e.g. a public static website bucket)
- The wildcard is part of a deny-all/allow-list pattern where the effective policy is restrictive

#### Error Handling and Failure Suppression
- A `terraform.tfstate` or `*.tfstate.backup` file included in the diff — state can hold plaintext
  secrets and resource attributes with no governance over who can read a failed-apply artifact
- A literal password, API key, access key/secret pair, private key, or connection string assigned
  directly to a resource argument or a `variable`/`locals` default instead of a secret manager or
  environment-backed data source, hiding a credential-rotation failure mode entirely

Do not report in the following cases:
- The value is an obvious placeholder or example clearly marked as such
- The secret is sourced from a `sensitive` input or data source already visible in the same file
