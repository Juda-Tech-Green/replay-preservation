# Contributing

Keep changes focused on reproducible preservation behavior. Open a discussion or issue describing the problem, input format and expected observation before adding a new acquisition or execution workflow. Never attach recovered commercial software, private evidence, credentials or personal paths to issues.

Create a Python 3.11+ virtual environment, install this checkout and run:

```bash
.venv/bin/python -m pip install .
.venv/bin/python -m unittest discover -s tests -v
```

Use synthetic payloads and temporary directories. Add meaningful tests for malformed metadata, incomplete reads, map/EOF/allocation disagreements, conflicting evidence and missing observations. Keep historical coverage, structural validity, package completeness, emulator compatibility, playability and authenticity separate. Do not change a past outcome to make a regression pass.

The public tree uses `src/replay_preservation/`. `scripts/replay.py` is only a checkout wrapper; the installed entry point is `replay-preservation`. Update CLI documentation and fixtures with behavioral changes. The code has no runtime Python dependencies. Proposed dependencies need a documented purpose, license and security review; never install host tools automatically.

Changes to display/input helpers do not establish a secure emulator environment. Test those helpers with harmless data. Physical reads, installations, recovered execution, retries and publication require their actual user-authorized scope; contributing code does not grant it.

Before proposing a release, run `python scripts/audit_public_tree.py`, review its findings, inspect distribution archives and regenerate the reviewed file manifest. Keep build environments, scanner output and packages outside the source tree. Git ignore rules do not replace a file-by-file publication review. See [security](SECURITY.md) and [first-push plan](FIRST_PUSH_PLAN.md).

Contributions must be original or appropriately licensed for inclusion under the project MIT license. The license does not cover any third-party recovered content. Keep infrastructure and documentation in English and preserve original software filenames/languages in private recovery workflows.

To reproduce the reviewed build, use a disposable virtual environment outside the source tree, install `requirements-build.txt`, then run `python scripts/build_public_release.py --out-dir <new-external-dist-directory>`. The builder audits the allowlist, builds an isolated source copy and normalizes source-archive ownership/timestamps. Inspect the resulting wheel and source archive. Plain build-tool defaults may embed a local account name in tar headers. These are build-only tools; the installed project itself declares no runtime Python dependencies.
