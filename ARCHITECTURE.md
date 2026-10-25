# Public alpha architecture

The installable `replay_preservation` package has an offline command interface and reusable library modules. It accepts explicitly supplied local copies and emits JSON observations or fresh derivatives. No private evidence or launch controllers are packaged.

| Layer | Modules | Implemented boundary |
| --- | --- | --- |
| CLI | `cli`, `__main__` | 13 deterministic offline operations; explicit arguments and expected hashes |
| Verification | `baseline`, `mapfile` | Regular-file guards, map/domain/status checks, stable hashes and independent evidence statuses |
| Filesystem | `iso_coverage` | Bounded cooked ISO 9660/Joliet metadata, multi-extents, recovered/EOF/sparse agreement |
| Derivation | `target_strategy`, `target_merge` | Proposal construction, compact target validation, new sparse derivatives, conflict rejection |
| Static formats | `signatures`, `doom_static`, `archives` | Conservative header identification, MZ/WAD bounds, guarded ZIP library utilities |
| Catalog/inference | `catalog`, `assessment`, `candidates`, `image_report`, `covered_components` | Developer APIs for traceable observations and priorities; some mutate supplied workspaces and are not offline CLI commands |
| Compatibility support | `bounded_process_capture`, `compat` | Bounded collection, viewer state/input/protocol helpers and regression policies; not a security sandbox |

The CLI has no acquisition or emulator-launch operation. Developer APIs can inspect a specifically supplied read-only mount or write a supplied catalog/report workspace; callers must distinguish those APIs from the guarded offline CLI and retain their own authorization and preservation boundaries. Historical orchestration scripts and their embedded local paths/permissions are excluded.

Inputs are private stable regular files. Symlink components, devices and optical filesystems are rejected by baseline CLI guards. Hashes are checked before use and rechecked afterward. These checks assume no malicious concurrent path replacement and do not replace OS isolation or quotas. File parsing and output operations can consume resources; parser bounds are not a universal hostile-input sandbox.

Derivative/extraction directories must be new. Failed operations retain explicit failure state and partial output for review. Recovered `+` claims must also agree with EOF and sparse allocation. Filesystem allocation differs by platform, so deterministic results mean unchanged bytes, paths, arguments and allocation on the same environment; absolute provenance paths are intentionally retained in private analysis output.

The JSON interchange contract v0.1 preserves independent statuses. Python release metadata is `0.1.0a0`; the human release label is `v0.1.0-alpha`. Existing private catalogs use stage-specific schema histories; this release checks supplied catalogs read-only and does not ship or migrate one.

The repository-local skill and documentation require a source checkout. The wheel provides the package, entry point, license, schema and proposal templates under the environment's shared data directory. No optical tools, emulator, X server or Tk installation is performed by the package. Optional Tk/X11 helper use is a developer concern outside the offline CLI.

[Workflow](WORKFLOW.md) · [CLI](CLI_REFERENCE.md) · [security](SECURITY.md) · [schema](PRESERVATION_SCHEMA.md)
