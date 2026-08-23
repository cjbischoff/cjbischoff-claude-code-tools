> Favor precision over recall: only raise a finding when the evidence in the
> properties file is confident, and stay silent when a key's consumer is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Missing Required Keys and Null-or-Empty Values
- A key documented or conventionally required by the framework (e.g.
  `spring.datasource.url`) is missing from a profile that needs it, or is present
  with an empty value that the consumer does not treat as "unset"
- A key whose value is a property placeholder (`${other.key}`) that references a key
  never defined anywhere in the visible file set

Do not report in the following cases:
- The key is optional per the framework's own documented default
- The placeholder resolves to a key defined in a properties file outside the diff's
  visible scope, with no evidence it is actually missing

#### Duplicate-Key Override and Load-Order Races
`.properties` files have no runtime threads, but duplicate keys create the same
silent-override hazard as a race:
- Duplicate key definitions within the visible scope of the current file, where the
  later value silently overrides the earlier one and both look intentional
- Do not report in the following cases:
  - The file format/loader explicitly documents last-value-wins as intended behavior
    and only one definition is meaningfully in use

#### Injection, Hardcoded Secrets, and Credentials
- A password, API key, database connection string, or private key stored in
  plaintext under a key like `*.password`, `*.secret`, `*.token`, or `*.apiKey`
- A JDBC/connection URL embedding a plaintext username and password instead of
  referencing an environment variable or secret store

Do not report in the following cases:
- The value is clearly a placeholder/example (`changeit`, `xxx`, `${DB_PASSWORD}`)
  in a template or sample properties file
- The file is scoped to local-only development and is excluded from version control
  elsewhere in the repo (e.g. covered by `.gitignore`), with that scoping visible

#### Resource Limits, Malformed Entries, and Escaping Errors
- A key-value pair missing the `=`/`:` separator, or with unescaped backslashes in a
  Windows path or Unicode escape that will be misinterpreted on load
- A multi-line value missing the trailing `\` continuation, silently truncating the
  value

Do not report in the following cases:
- The escaping is already correct for the loader in use (e.g. properly doubled
  backslashes)
- No evidence the malformed-looking value is actually consumed as a path/pattern

#### Swallowed Validation Errors on Load
- A boolean/numeric-typed key given a value that fails to parse as that type
  (e.g. `timeout=abc` for an integer timeout), when the consumer silently falls back
  to a default instead of failing startup
- Do not report in the following cases:
  - The consumer is not visible in the diff and no type contract is established
  - The value already matches the expected type
