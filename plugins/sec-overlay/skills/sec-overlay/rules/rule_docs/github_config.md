> Favor precision over recall: only raise a finding when the evidence in the `.github/` config
> under review is confident, and stay silent when repository label/team state is not visible in
> the diff. Adapted from open-code-review (Apache-2.0).

#### Missing Required Fields and Optional Input Validation
- An issue template missing `name`, `description`, or `body`, or a form input missing `id` so it
  cannot be parsed programmatically
- A dropdown-type input declared with an empty `options` list

Do not report in the following cases:
- The field is explicitly documented as optional by the template schema
- The block is markdown-only with no input, where `id` legitimately does not apply

#### Category Label Synchronization Across Repository State
- A `release.yml` category referencing a label in `categories[].labels` that does not exist
  anywhere else in the repository's configuration
- A `release.yml` with no catch-all (`*`) category, silently omitting PRs from release notes
  depending on which labels happen to be applied

Do not report in the following cases:
- The label is created in the same PR/commit that adds the config
- The omission of a catch-all is a documented, intentional allow-list of categories

#### Injection via Unescaped Template Placeholders
- A CODEOWNERS entry, funding config, or template body embedding a dynamically-sourced value that
  is later rendered into an issue/PR body without sanitization
- A config field holding untrusted, externally-fetched content instead of a static literal

Do not report in the following cases:
- The value is a static literal set directly by a maintainer
- The field is documented by GitHub as always rendered as unrendered plain text

#### Overbroad CODEOWNERS Resource Scope
- A CODEOWNERS rule using a bare wildcard (`*`) that grants review authority over the entire
  repository where a narrower path pattern was clearly intended
- An issue-template category or dropdown enabled for all repository members with no scoping,
  where sibling entries in the same file restrict by team

Do not report in the following cases:
- The wildcard is the intentional top-level fallback owner
- Sibling entries in the same file also use unscoped wildcards, so this is a pre-existing pattern

#### Silent Error Handling in Config Parsing
- A misspelled key in `dependabot.yml`, CODEOWNERS, or an issue-template config that a permissive
  parser ignores instead of erroring, silently disabling the intended setting
- A spelling error in a YAML key (e.g. `versioning-stratgey` instead of `versioning-strategy`)
  causing the configuration to be ignored

Do not report in the following cases:
- The key is validated by a schema check in CI that would already catch the typo
- The misspelling is inside a free-text value, not a configuration key
