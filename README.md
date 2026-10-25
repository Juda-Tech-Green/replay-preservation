# RE Preservation

**v0.1.0-alpha** — offline tools for evidence-based historical software recovery.

RE connects acquisition maps, filesystem extents, verified working copies, static checks and scoped human observations. It helps distinguish recovered bytes from missing data and limited gameplay from complete functional validation.

This repository contains original project code, documentation and synthetic tests. It contains **no game files, disc images, saved games, private catalogs or raw acquisition evidence**. The [MIT license](LICENSE) covers the original project materials; it grants no rights to third-party games or other recovered content.

## Install and run

Linux with Python 3.11 or later is required. The CLI uses only the Python standard library and Linux mount metadata. No optical tools or emulator are required for normal offline commands.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/replay-preservation --version
.venv/bin/replay-preservation --help
.venv/bin/replay-preservation pilot-plan --disc-id disc02-pilot
.venv/bin/replay-preservation validate-record templates/preservation_record.json
```

The display release name is `v0.1.0-alpha`; Python package metadata uses the equivalent alpha form `0.1.0a0`. After installation, `python -m replay_preservation` and `python scripts/replay.py` expose the same CLI. Use the virtual environment's Python when invoking those alternatives.

## Implemented capabilities

- SHA-256 verification and strict GNU ddrescue map parsing against an expected domain.
- Cooked ISO 9660/Joliet metadata inspection and file/sector coverage, including EOF and sparse-hole checks.
- Compact target-chunk validation, absolute-offset translation and fresh derivative/map generation with conflict rejection.
- Verified extraction of fully sector-covered known packages and bounded MZ/WAD structural checks.
- Read-only SQLite integrity checks, independent preservation-status records and offline V2 session summaries.

Commands analyze explicitly supplied local regular files. They do not mount media, run ddrescue, install tools, execute recovered software, launch emulators or mutate a catalog. `merge-target` and `extract-package` write only fresh output directories. A partial target can be analyzed successfully without being eligible for merge.

Some developer library modules retain mounted-assessment and catalog-writing helpers; they are not exposed by the offline CLI. Experimental viewer/protocol helpers are included for regression coverage, **not as a portable security sandbox or approved game launcher**. See [architecture](ARCHITECTURE.md) and [security](SECURITY.md).

## Evidence before conclusions

Map `+` coverage does not independently establish historical integrity. Zero-filled missing regions and sparse holes are never promoted to authentic recovered data. A known package set is not an exhaustive dependency proof. Human confirmation of a defined gameplay scope is distinct from emulator startup, sound compatibility or full functional validation.

The [Disc 01 DOOM II case study](docs/case-studies/disc-01-doom2.md) shows how targeted recovery enabled human-verified MAP01 controls while the whole-disc image remained partial. Pause/resume, audio and historical publisher authenticity remain unverified or untested.

## Development

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests generate synthetic ISO, executable-header, WAD, archive and map data in temporary directories; no recovered program is executed. Two optional GNU ddrescue tests use synthetic regular files and skip if the existing tool is absent. GUI-policy tests skip if optional Tk is unavailable; no graphical window or display connection is opened by the suite. No software is installed by the tests.

## Documentation

- [CLI reference](CLI_REFERENCE.md) and [end-to-end workflow](WORKFLOW.md)
- [Preservation schema](PRESERVATION_SCHEMA.md) and [Disc 02 pilot plan](DISC02_PILOT_PLAN.md)
- [Repository-local Codex skill](.agents/skills/replay-preservation/SKILL.md)
- [Contributing](CONTRIBUTING.md), [security](SECURITY.md), [roadmap](ROADMAP.md), [changelog](CHANGELOG.md)
- [Release readiness](PUBLIC_RELEASE_READINESS.md), [file manifest](PUBLIC_FILE_MANIFEST.md), [security audit](PUBLIC_SECURITY_AUDIT.md), [release notes](RELEASE_NOTES_v0.1.0-alpha.md), [first-push plan](FIRST_PUSH_PLAN.md)

This is an alpha release candidate prepared for review. Publication and the first Git push require separate authorization. No historical execution authorization is shipped or transferable through this repository.
