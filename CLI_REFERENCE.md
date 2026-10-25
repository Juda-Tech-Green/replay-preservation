# Python CLI reference — v0.1

Use Linux and **Python 3.11+**. Install this checkout into a virtual environment as described in [README.md](README.md), then run `replay-preservation --help` using that environment. `--version` reports the alpha release and evidence-schema baseline versions. Nothing in this CLI mounts media, reads optical devices, installs packages, executes recovered programs, starts emulators or writes the catalog.

All inputs must be stable regular local files without symlink components, outside iso9660/udf mounts. Work in private directories without concurrent writers. SHA-256 arguments are expected lowercase hashes from a preserved verification record, not values silently trusted from an unreviewed file. Image/chunk operations verify them before use and recheck inputs afterward. Hashing intentionally reads whole files; static parsers cap input at 128 MiB and JSON/maps/events at 16 MiB. Compact target validation is capped at 128 MiB in v0.1. Sparse extent discovery must be supported by the host filesystem.

Successful analysis returns 0 and JSON on stdout. Analysis of a partial image/target can succeed while reporting partial coverage. Invalid arguments, failed checks or unsupported input return 2; argparse usage errors use normal help text, operation errors use `replay.preservation.error.v0.1` JSON on stderr. An unexpected programming failure is nonzero and must not be treated as a result. `--help`/`--version` return 0 with text.

| Command | Required arguments | Effects |
| --- | --- | --- |
| `hash` | positional path; optional `--expected SHA256` | Hashes one regular file; checks expected value if given |
| `map-summary` | `--map PATH --expected-size BYTES` | Reports read/bad/untried/etc bytes, unmapped bytes and recovery percentage against expected size |
| `coverage` | image arguments plus `--offset BYTES --length BYTES` | Intersects map, EOF and sparse allocation; no metadata inference |
| `inspect-image` | image arguments plus `--namespace Joliet` or `ISO9660` | Bounded metadata traversal and file/sector coverage; hashes fully covered files |
| `extract-package` | image arguments, namespace, `--package PREFIX --output-dir NEW_DIR` | New read-only-permission extracted files and extent/hash manifest; refuses incomplete enumeration or uncovered known files |
| `validate-target` | `--chunk PATH --map PATH --chunk-sha256 HASH --map-sha256 HASH --offset BYTES --length BYTES` | Validates compact local-zero chunk against absolute target-map coordinates; partial result stays partial |
| `merge-target` | merge arguments below | Fresh sparse derivative, combined map, verification and provenance; no in-place patch |
| `static-check` | positional path, `--kind mz` or `wad` | Bounded header/directory/record checks; does not prove runtime behavior |
| `validate-record` | positional JSON path | Checks baseline observation fields, independent statuses and minimum scoped human evidence |
| `verify-manifest` | `--manifest PATH --root DIRECTORY` | Verifies canonical relative-path SHA-256 map; no schema guessing |
| `catalog-check` | `--catalog PATH` | Read-only integrity, foreign keys and table counts; connection explicitly closed |
| `session-summary` | `--viewer PATH --worker-events PATH --controller PATH`; optional `--human PATH` | Offline V2 adapter; preserves raw results and follow-up separately; rejects synthetic runs as actual play |
| `pilot-plan` | `--disc-id ID` | Emits a preparation-only checklist; no media access or execution permission |

“Image arguments” means all four of `--image PATH --map PATH --image-sha256 HASH --map-sha256 HASH`. Image origin must be cooked ISO sector zero, not a raw BIN track without a validated translation. `coverage` accepts nonnegative byte offsets; target operations additionally require 2048-byte alignment and a positive length.

## Examples

These use placeholders for private verified **copies**. Replace hashes and paths explicitly; no physical source path belongs here.

```bash
replay-preservation hash work/disc.iso --expected EXPECTED_SHA256
replay-preservation map-summary --map work/disc.map --expected-size 655992832
replay-preservation inspect-image --image work/disc.iso --map work/disc.map --image-sha256 IMAGE_SHA256 --map-sha256 MAP_SHA256 --namespace Joliet
replay-preservation validate-target --chunk work/T01.chunk --map work/T01.map --chunk-sha256 CHUNK_SHA256 --map-sha256 TARGET_MAP_SHA256 --offset 434634752 --length 688128
```

T01's recorded input offset was `212224 × 2048 = 434634752`; its 336 sectors occupied LBAs 212224–212559. Its compact chunk byte zero corresponded to that absolute offset. The map's unrelated `?` regions do not make the target incomplete when the authorized interval is fully recovered.

```bash
replay-preservation merge-target \
  --base-image work/base.iso --base-map work/base.map \
  --base-sha256 BASE_SHA256 --base-map-sha256 BASE_MAP_SHA256 \
  --chunk work/T01.chunk --target-map work/T01.map \
  --chunk-sha256 CHUNK_SHA256 --target-map-sha256 TARGET_MAP_SHA256 \
  --offset 434634752 --length 688128 --output-dir work/new-derivative
```

The output directory's parent must already exist; the directory itself must not. Outputs are `image.iso`, `combined.map` and `provenance.json`. Conflicting previously recovered bytes abort. A failed operation leaves `FAILED.json` and any partial files for review; do not use them or retry into that directory.

```bash
replay-preservation extract-package --image work/derived.iso --map work/combined.map --image-sha256 IMAGE_SHA256 --map-sha256 MAP_SHA256 --namespace Joliet --package DOOM2 --output-dir work/new-static-stage
replay-preservation static-check work/new-static-stage/files/DOOM2/DOOM2.EXE --kind mz
replay-preservation static-check work/new-static-stage/files/DOOM2/DOOM2.WAD --kind wad
replay-preservation validate-record templates/preservation_record.json
replay-preservation catalog-check --catalog work/catalog.sqlite
replay-preservation pilot-plan --disc-id disc02-pilot
```

Save stdout only to a **new** artifact path; shell redirection can overwrite files independently of the CLI. Analysis JSON contains private absolute paths and is not a publication package. Manifests use `{ "schema":"replay.preservation.manifest.v0.1", "sha256": {"relative/path":"lowercase digest"} }`. A copied historical manifest requires an explicit format conversion retaining its original provenance.

The public package excludes historical one-off orchestration scripts, private launch configurations and evidence. Developer library APIs for mounted assessment, catalog/report writing and display/protocol support are not exposed as offline CLI operations. They must not be confused with a portable acquisition or secure game-launch service.
