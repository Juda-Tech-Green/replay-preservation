# Public release readiness — v0.1.0-alpha

**Disposition: clean export ready for owner review; publication not authorized.** No Git repository, index, commit, tag or push has been created. The target repository was checked with a read-only ref query and returned no refs at preparation time; repeat that check before any authorized first push.

## Verified implementation

- Read the baseline README, CLI/workflow/schema/pilot documentation, skill and implementation audit; inspected source, synthetic fixtures and historical test boundaries. The original workspace had no packaging configuration.
- Reran the original suite: **88 tests passed**. The source CLI's help, version and preparation-only pilot operation also ran successfully, with bytecode writes disabled.
- Built a separate `src/` package with installed `replay-preservation`, `python -m replay_preservation` and checkout-wrapper interfaces. Every one of the **13 CLI operations** is exercised against generated temporary artifacts, including extraction and merge.
- Public suite: **97 tests passed**, including the original regression cases and nine public packaging/security tests. The same suite was exercised against the installed wheel in a separate fresh virtual environment. The runtime package declares no Python dependencies; `pip check` passed.
- Wheel and source distribution build successfully through the reviewed builder, with normalized source-archive ownership/timestamps. The source distribution includes tests, docs, schemas, templates and the repository-local skill; the wheel carries installable code, license and schema/template shared data.
- Skill frontmatter, normal repository-local discovery location, internal document links and referenced script paths were verified. No global skill installation was performed.
- Exact public file allowlist, per-file review manifest and static scanner are provided. No private evidence, proprietary software, personal paths or copied Git history is included.

## Interpretation and limits

This is a Linux/Python 3.11+ alpha; validation was performed on Python 3.14 in fresh virtual environments on the current Linux host. It is not a cross-platform or multi-version certification. Optional ddrescue regressions operate on synthetic regular files only; optional Tk policy tests open no window. No actual game/emulator session is rerun for this release.

The case study supports limited human-verified MAP01 interaction, not full functional validation or historical publisher authenticity. Pause/resume, audio, later levels, saves and other limits remain explicit. Whole-disc recovery was partial even though the known DOOM2 package became sector-covered.

The offline CLI does not acquire media, launch software, install tools or mutate a catalog. Developer mounted-assessment/catalog/X11 functions have different effects and are not security-reviewed general launchers. See [security audit](PUBLIC_SECURITY_AUDIT.md) for scanner and sandbox limits.

## Remaining approval steps

No engineering/export blocker was found in the reviewed candidate. Publication is intentionally blocked pending explicit owner authorization. Because Git initialization is prohibited before that authorization, an actual tracked-index audit cannot yet exist; the proposed exact file set has been audited instead. The [first-push plan](FIRST_PUSH_PLAN.md) requires index/diff review before any commit or push. Tags, GitHub releases and package uploads need their corresponding scope.

Review [PUBLIC_FILE_MANIFEST.md](PUBLIC_FILE_MANIFEST.md), [LICENSE](LICENSE), [release notes](RELEASE_NOTES_v0.1.0-alpha.md) and the full candidate before approving publication. Any changes invalidate the current manifest and require renewed verification.
