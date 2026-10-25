# First-push plan — authorization required

Target repository: https://github.com/Juda-Tech-Green/replay-preservation

The clean export is a review candidate. It has no `.git`, inherited history, staged files or commit. Do not run the steps below until the export audit passes **and the owner explicitly authorizes publication**. No command here was executed as part of preparation.

1. Review `PUBLIC_RELEASE_READINESS.md`, `PUBLIC_SECURITY_AUDIT.md`, `PUBLIC_FILE_MANIFEST.md`, license scope and the complete proposed file list in `public-release-files.json`. Repeat `python scripts/audit_public_tree.py` immediately before publication; any changes need renewed review/manifest generation.
2. Confirm that the target URL and intended visibility remain correct and remote refs are still empty. Do not overwrite a populated remote or import private development history.
3. Only after explicit authorization, initialize a fresh Git repository in this clean export, set the branch to `main` and configure the target remote. Use the owner's existing Git identity; never copy credentials into project files.
4. Stage **only** the explicit paths in `public-release-files.json`. Do not use a broad recursive add as a substitute for the reviewed allowlist. Inspect `git ls-files --stage`, `git status --short` and `git diff --cached --stat`, then review the full staged diff. Rerun the audit with tracked-file checks enabled. A candidate-file audit before Git initialization is not a claim that a real index has already been inspected.
5. Commit only after the staged paths and content match the reviewed manifest. Recheck the new tree for unwanted payloads, secrets, local paths and generated build files. A commit changing the reviewed contents requires another audit.
6. Push the reviewed `main` commit only within the explicit publication authorization. Do not force-push. GitHub push may invoke account/repository checks; stop and report rejection rather than bypassing them.
7. A `v0.1.0-alpha` tag, GitHub release, release asset upload or package-index upload requires the corresponding authorized scope. The repository push does not automatically authorize all of those actions. Use the prepared release notes only after verification of the exact committed tree.

Use `scripts/build_public_release.py` to audit/build a source copy and normalize private archive ownership metadata. Optional distribution archives were built for verification outside this source tree. Inspect their contents and license metadata before attaching any separately approved release asset. Do not attach private logs, databases, images or game files.
