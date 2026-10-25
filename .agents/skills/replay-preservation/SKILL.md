---
name: replay-preservation
description: Assess historical software recovery artifacts, verify sector coverage and compact target chunks, prepare static package validation, and record scoped compatibility evidence in an RE preservation checkout. Use for preservation workflows; it does not authorize optical acquisition or recovered-program execution.
---

# RE preservation

Work from this source checkout after installing the package in a virtual environment. Use `replay-preservation` or the checkout wrapper `scripts/replay.py` with that environment. This skill is repository-local: relative document links resolve within the same checkout. Infrastructure and reports use English; preserve recovered filenames and content unchanged.

Start with the requested stage and available artifacts, not a physical reread. Use the offline CLI in [CLI_REFERENCE.md](../../../CLI_REFERENCE.md); it accepts explicit paths/hashes, creates fresh derivative/extraction directories, and has no acquisition or launch command. Historical private orchestrators are excluded. Developer library APIs that write catalogs/reports or inspect mounts have different effects from the offline CLI.

Read only the relevant references:

- [WORKFLOW.md](../../../WORKFLOW.md): transitions, evidence requirements, acquisition/execution boundaries and stopping conditions.
- [PRESERVATION_SCHEMA.md](../../../PRESERVATION_SCHEMA.md): independent stage statuses and interchange observations. Validate new records with `validate-record`; preserve existing free-text catalog history.
- [ARCHITECTURE.md](../../../ARCHITECTURE.md): reusable modules and unsupported formats/geometry.
- [Disc 01 case study](../../../docs/case-studies/disc-01-doom2.md): interpreting the actual Disc 01 recovery, incomplete attempts and limited gameplay result.
- [DISC02_PILOT_PLAN.md](../../../DISC02_PILOT_PLAN.md): starting a separately identified disc without borrowing Disc 01 permissions or facts.

Keep these preservation invariants:

- Original images, acquisition maps/logs, prior reports and test results remain unchanged. Hash verified copies and record each derivation's inputs, outputs, exact coordinate translation and limitations. Do not publish images, recovered game files or private evidence.
- A ddrescue `+` range supports availability only where bytes exist and are not sparse holes. Unknown or zero-filled regions are not authentic recovered data. Compact target byte zero may correspond to a nonzero absolute disc offset; validate that translation before merging. Conflicting recovered overlaps stop derivation.
- Sector coverage, bounded structural integrity, known package completeness, emulator compatibility, actual playability and historical authenticity are independent. A known file set is not an exhaustive dependency proof. Human-confirmed MAP01/control checks support limited interactive play only.
- Preserve raw UI results and later human clarification separately. Missing menu/transition markers remain unknown; confirmation time is not event time. A post-game frame does not prove gameplay. Synthetic checks cannot establish real playability. A supervisor deadline alone is not a game crash.
- In future DOOM II test instructions use physical **Pause/Break**, not P. Do not edit historical viewer records or their readiness hashes to correct old guidance. Sound remains untested when disabled.

Optical reads, installations and recovered execution require their actual user-authorized scope. This skill and proposal templates grant none. When such work is requested, first make the exact inputs, commands, environment and limits reviewable; obtain missing authorization immediately before the action. Existing authorization may be used only within its unconsumed scope. Do not replay a consumed session lock, automatically retry, weaken isolation, load excluded historical saves or run multiplayer helpers. Known physical damage stops reads.

For a newly authorized interactive test, retain reviewed filesystem/network/device/display isolation and separately reviewed wall/CPU/memory limits; run harmless boundary probes first. Use only the existing allowlisted input/private framebuffer protocol. Record human observations, bounded screenshots/logs, termination reason, cleanup and before/after hashes. Ask for specific missing observations rather than converting general positive feedback into every check passing.

For development run `.venv/bin/python -m unittest discover -s tests -v` with synthetic fixtures. Do not place proprietary payloads in tests. Baseline CLI catalog checks are read-only; any future catalog writer needs a snapshot, append-only observations and integrity checks. Report blockers and unsupported layouts explicitly instead of inventing successful recovery.
