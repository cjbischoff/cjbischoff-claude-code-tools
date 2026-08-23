> Favor precision over recall: only raise a finding when the evidence in the Bicep
> under review is confident, and stay silent when context is unclear. Adapted from open-code-review (Apache-2.0). Do not infer Azure subscription/tenant state or
> deployed resource state that lives outside this file.

#### Missing Required Parameters and Insecure Nullable Defaults
- A parameter used by a resource property that is declared optional with no default,
  when the resource property is required for the deployment to succeed
- A parameter whose name or description clearly indicates a credential (password,
  secret, token, connectionString, apiKey) declared without the `@secure()`
  decorator, letting the value appear in deployment history/logs

Do not report in the following cases:
- The parameter already has a safe, documented default for the optional case
- The parameter is already marked `@secure()`

#### Deployment Concurrency and Non-Deterministic Ordering
Bicep has no runtime threads, but resource deployment ordering has an analogous
race hazard:
- A resource that implicitly depends on another (via a property reference) but the
  reference is missing, risking parallel deployment ordering that fails or produces
  a misconfigured resource
- Do not report in the following cases:
  - The dependency is already established via a symbolic reference or explicit
    `dependsOn`
  - No evidence two resources in the diff have an ordering requirement

#### Injection, Hardcoded Secrets, and Overly Permissive Access
- A literal password, connection string, API key, or access token assigned directly
  to a resource property or variable instead of a Key Vault reference or secure
  parameter
- A `Microsoft.Authorization/roleAssignments` resource granting `Owner`/`Contributor`
  at subscription or resource-group scope where a narrower role would suffice
- A network security group rule with `sourceAddressPrefix` set to `*`/`Internet` on
  a sensitive port (22, 3389, 3306, 5432, 1433, 27017)

Do not report in the following cases:
- The secret already comes from `getSecret()` or a `@secure()` parameter
- Sibling role assignments in the same file already use the same broad scope
  consistently for a documented reason

#### Insecure Defaults and Missing Resource Limits
- A storage account without `minimumTlsVersion` set to a current version, or with
  `supportsHttpsTrafficOnly` explicitly set to `false`
- A resource property that disables encryption-at-rest where the resource type
  supports enabling it
- Do not report in the following cases:
  - The diff merely omits an optional hardening property with no explicit insecure
    value shown
  - The resource type does not support the property in question

#### Swallowed Validation Errors and Version Drift
- An `api-version` in a resource's type string that is unusually old relative to
  sibling resources of the same provider in the same diff
- A module reference with no version/tag pinning where the surrounding file
  otherwise pins versions, silently picking up unreviewed changes on redeploy

Do not report in the following cases:
- The `api-version` is consistent with all sibling resources of that provider
- No other module reference in the file pins a version, so there is no inconsistency
