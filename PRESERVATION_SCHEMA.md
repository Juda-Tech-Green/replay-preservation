# Preservation evidence schema v0.1

`schemas/preservation-record-v0.1.schema.json` specifies new interchange observations. `templates/preservation_record.json` is an example, not a real Disc 02 event. Validate with `.venv/bin/replay-preservation validate-record <record.json>`. The CLI implements required-field, status, UTC, hash and scoped-human-evidence checks without an external JSON Schema dependency; the published JSON Schema additionally describes structural types for external tooling.

A record has `schema`, stable `disc_id`, caller-supplied `recorded_utc`, `operation`, hashed `inputs`, independent `statuses`, source-attributed `evidence`, `limitations`, and optional `scope`/historical `authorization`. Use UTC with zero offset for recorded events; render local times explicitly when helpful. Collection time is not an invented gameplay-event time. Paths preserve originals; public derivatives should use reviewed aliases. Hashes fix an observed state, not its publisher authenticity. An authorization field documents an event and cannot authorize a later run.

| Dimension | Values | Interpretation |
| --- | --- | --- |
| acquisition | `not_assessed`, `partial`, `complete`, `failed` | Expected domain/geometry and all acquisition artifacts must support completeness |
| sector_coverage | `not_assessed`, `full`, `partial`, `unavailable`, `unknown` | `full` needs map, EOF and allocation agreement for required sectors |
| file_integrity | `not_assessed`, `readable_unverified`, `structural_checks_passed`, `check_failed`, `changed` | State inspected properties; failed check is not automatic proof of historical corruption |
| package_completeness | `not_assessed`, `known_set_complete`, `known_set_incomplete`, `unknown` | Known file set only; document dependency assumptions |
| emulator_compatibility | `not_tested`, `prepared`, `startup_verified`, `interactive_partial`, `checks_passed`, `failed`, `inconclusive` | State environment and tested capabilities |
| actual_playability | `not_tested`, `unverified`, `limited_interactive_verified`, `defined_scope_verified`, `failed` | Verified values require explicit scope and passing human evidence; never mean universal functionality |
| historical_authenticity | `unverified`, `reference_match`, `conflicting_reference` | Name the authenticated reference, version and comparison; no implication from readability |

No total ordering or global “valid” promotion connects these dimensions. A partial image can contain a fully covered package; a structurally valid executable can fail to start; MAP01 controls can pass while pause/audio remain unverified. The record validator verifies the record's structure and evidence presence, not the truth of submitted observations.

Evidence entries should identify the check, result, source (`human_confirmation`, parser, emulator log or synthetic regression), UTC/elapsed time when actually observed, artifact path/hash and caveats. Preserve original UI findings and later clarifications as separate observations. Synthetic evidence cannot establish actual playability. No automatic confidence score is assigned; use explicit facts and limitations.

## Other baseline outputs

- `replay.preservation.analysis.v0.1`: deterministic `operation`, verified `inputs` (path/size/SHA-256), and operation-specific `result`. Successful analysis is not successful recovery. Extent coordinates are byte offsets in cooked ISO domain unless explicitly documented otherwise.
- `replay.preservation.error.v0.1`: failed operation plus English error; exit code 2. Do not use partial output as a result.
- `replay.preservation.manifest.v0.1`: `sha256` map of relative contained paths to lowercase SHA-256; verifier rejects traversal and symlinks. Original historical manifest formats are retained; convert a copy explicitly rather than guessing schemas.
- `replay.preservation.session-proposal.v0.1`: future workflow template with `execution_authorized:false`; not an executable or permission token.
- Merge/extraction `provenance.json`/`manifest.json`: hashed inputs/outputs or per-file extents and inspected state; `FAILED.json` takes precedence after any error.

## Existing SQLite lineage

The catalog retains `discs`, `files`, `software`, `recovery_events`, `compatibility_tests`, `reconstructions` and `file_extents`; later stages add assessment runs/entries, candidate observations, image investigations/file/extent coverage/package coverage, and `software_validation_runs`. Existing `schema_info` versions and descriptive historical statuses remain as recorded. The new JSON contract does not rewrite those tables or backfill fabricated observations.

`software_validation_runs` already separates sector coverage, file integrity, package completeness, emulator compatibility and actual playability with provenance JSON. `compatibility_tests` retains each attempt; `software.compatibility_status` is a current summary, not history. Future migration should append an interchange record or provenance link, preserve the old rows, snapshot the catalog, enable foreign keys and verify integrity. Baseline `catalog-check` is read-only and deliberately performs no migration. The public export contains no Disc 01 catalog and does not modify the private history.
