> Favor precision over recall: report only defects likely real in the changed schema
> and its reachable application, migration, and datasource context. Adapted from open-code-review (Apache-2.0).

#### Optional Relations and Nullability Mismatches
- A relation field whose optionality, scalar foreign-key field, `fields`, or
  `references` declarations disagree, allowing an invalid or unrepresentable
  relationship
- Adding a non-null field without a safe backfill/default/migration strategy for
  existing rows, forcing a NULL where the schema now forbids one

Do not report in the following cases:
- The relation/field optionality already matches its `fields`/`references` pair
- A migration or default in the same diff safely backfills existing rows

#### Migration Ordering Races
Prisma has no application-level threads in the schema itself, but migration rollout
has a real ordering hazard:
- A schema change (new required column, renamed column) applied without a migration
  that runs before the corresponding application-code deploy, risking old code
  writing rows the new schema rejects during the rollout window
- Do not report in the following cases:
  - The migration and application-code change are already sequenced/documented in
    the diff
  - The change is additive only (new optional field) with no deploy-order hazard

#### Raw Query Injection and Hardcoded Credentials
- `$queryRaw`/`$executeRaw` (or `Raw` variants) built by string concatenation of
  untrusted input instead of tagged-template parameter binding
- A hard-coded database URL, credential, or connection parameter in the schema or
  associated Prisma configuration where it can be committed or deployed to the wrong
  environment

Do not report in the following cases:
- The raw query uses the tagged-template form with values passed as parameters, not
  concatenated into the SQL text
- The datasource URL is sourced from an environment variable at deploy time

#### Resource Leaks: Missing Indexes and Connection-Pool Sizing
- A unique constraint or index removed/missing when application queries or relation
  lookups demonstrate a concrete need, causing an unbounded table scan on a hot path
- A connection-pool or `relationMode`/datasource setting changed in a way that
  removes database-enforced integrity or exhausts connections under load, with no
  compensating application safeguard

Do not report in the following cases:
- No query or relation-access evidence in the diff establishes a concrete need for
  the index
- The pool/mode change is a documented workaround for a stated database limitation

#### Swallowed Migration and Validation Errors
- Removing, renaming, or narrowing a field/enum value in a way that can fail a
  migration or silently drop data, without the diff showing the migration handles it
- A generator or preview-feature change that can break client generation without a
  corresponding build/CI check catching the failure

Do not report in the following cases:
- The change is accompanied by a migration, generated-client update, or application
  code change reviewed together in the same diff
- The enum/field change is additive only
