# Public security audit — v0.1.0-alpha candidate

Scope: the explicit proposed public files, synthetic tests, installed package and distribution archives. This is a release hygiene/security review, not a penetration test, exhaustive vulnerability assessment or legal certification. Verification environments and raw scanner logs stay outside the public source tree.

| Check | Result and method |
| --- | --- |
| Export isolation | New source tree; selected text/code files only. No copied private history, approval files or raw evidence. Original workspace protected by a before/after content manifest. |
| Git tracked files | **No Git repository initialized; no index or tracked files exist.** Exact proposed contents reviewed through `public-release-files.json` and `PUBLIC_FILE_MANIFEST.md`. Actual index audit is required after separately authorized initialization/staging and before commit. |
| Secret scanning | Reviewed-manifest content hashes are checked as well as file names. Custom static patterns for private keys, GitHub tokens, AWS key IDs, JWTs, credential assignments/URLs; no unresolved matches in the reviewed candidate. Scanner never prints matched secret values. |
| Large files | 1 MiB per-file gate; candidate files are small UTF-8 source/documentation/JSON. Oversized inputs are rejected before content scanning. |
| Copyrighted/binary payload | Forbidden filename extensions, NUL/non-UTF-8 and executable/archive/database/image signatures checked. No game binaries, WADs, ISO/BIN images, saves, private databases or raw evidence included. Source literals and game filenames in tests/docs are not distributed game files. |
| Personal/absolute paths | No personal home directories, private acquisition paths, email addresses or embedded account credentials found. Generic Linux API/sandbox/test paths remain where code requires them. Public examples use relative `work/` paths. |
| License scope | MIT for original project code/documentation. No rights to games, trademarks, recovered data or separately installed tools are implied. Product names are descriptive; no affiliation claimed. |
| Python runtime dependencies | None declared. Standard-library CLI; optional Tk and system X11 helpers are developer-only. GNU ddrescue integration tests use an existing tool on synthetic regular files or skip. No emulator/optical tool installation occurs. |
| Fixture review | One metadata-only Disc 01 JSON fixture; byte patterns, archives, ISO structures and format headers generated temporarily by tests. No external game download, execution or fixture payload included. |
| Packaging | Wheel/source archive inspected for file set, paths, forbidden payloads and metadata. The release builder normalizes source-archive UID/GID/owner names and timestamps; the initial unnormalized build was rejected during review. Wheel has original package code, license, schemas and proposal templates; no evidence. |
| Documentation/skill | Internal links and referenced checkout paths checked; skill frontmatter validated. Skill grants no acquisition/execution/publication permission. |

## Improvements made only in the clean export

- Moved reusable code to `src/replay_preservation` and excluded historical private controllers and orchestrators.
- Removed private absolute paths from copied source/docs and rewrote the public overview/case study.
- Preserved transaction semantics while explicitly closing copied SQLite connections.
- Replaced assertion-only protocol/input/state/database checks with explicit validation where present, including optimized-Python regression coverage.
- Corrected the exported viewer's Pause/Break hint. Original private viewer code and historical results remain unchanged.
- Added an audited-copy release builder and a reproducibility/owner-sanitization regression after detecting local ownership in an initial source archive.
- Added a regression-tested allowlist scanner with traversal/link, injected-token, unexpected-binary and personal-path cases. Installation/test commands do not execute recovered software.

## Reviewed build-only tools

Fresh disposable build environment: `build 1.6.1` (MIT), `setuptools 84.2.1` (MIT), `wheel 0.48.0` (MIT), `packaging 26.3` (Apache-2.0 OR BSD-2-Clause), `pyproject-hooks 1.3.3` (MIT), as reported by installed distribution metadata. Exact versions are in `requirements-build.txt`. These tools are not bundled into the project wheel and are not runtime dependencies. No claim of a current CVE-database audit is made.

## Limits and publication gate

Pattern scanning cannot detect every secret, encoded payload or copyright problem. Human source/fixture and manifest review remains necessary. Hashes and scans do not authenticate historical games. Private-input path checks assume stable files without hostile concurrent writers. Experimental viewer/X11 helpers are not a portable sandbox or assurance that a host display is private. Parsing hostile or very large files still requires reviewed OS limits.

No unresolved export finding is accepted silently. Publication is intentionally pending owner review; no commit, remote write, tag or release upload has occurred. The actual Git index must be audited after authorized initialization. Repeat the scanner and manifest review after any edit.
