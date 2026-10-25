# Disc 01: limited DOOM II recovery from a partial image

A historical software compilation CD suffered prolonged read failures. The preservation objective was to identify what was available, preserve the original acquisition artifacts and test only a verified working package under isolation. This case study reports selected technical facts; private evidence, game payloads, screenshots, save files and local database records are not published here.

## Acquisition and the incomplete disc

The initial GNU ddrescue acquisition was interrupted after prolonged failures. Its map described a 655,992,832-byte cooked-image domain:

| Map state | Bytes |
| --- | ---: |
| Recovered (`+`) | 147,324,928 |
| Untried (`?`) | 490,561,536 |
| Non-trimmed (`*`) | 18,102,272 |
| Bad-sector (`-`) | 4,096 |

Only about **22.458%** was recovered. Untried and non-trimmed bytes were retained as separate states, not all counted as proven unreadable sectors. The recovered region was contiguous at the beginning of the image. No claim of complete track/session preservation or physically undamaged media followed from these statistics.

## Sector-coverage assessment

ISO 9660/Joliet metadata was inspected from a regular local working image, using the map to gate reads. File extents were intersected with recovered ranges, actual EOF and sparse allocation; zero-filled missing regions were not treated as authentic data. Independent extent corroboration was retained privately.

Of 1,058 files, 711 were fully sector-covered, one was partial and 346 were unavailable. A covered file could be inspected and hashed, but that did not establish historical integrity or playability.

## T01 targeted recovery

The missing DOOM2 executable lay at LBAs **212224–212559**: 336 sectors, 688,128 bytes, beginning at absolute byte 434,634,752. A separately authorized bounded GNU ddrescue attempt recovered that target into a fresh compact chunk with no reported read errors.

Chunk byte zero corresponded to absolute disc byte 434,634,752. The target map retained absolute input coordinates and also listed unrelated untried portions of the disc. Its whole-domain percentage therefore was not the percentage recovered for the authorized target. Validation checked all 336 target sectors, allocation, file length and hashes before integration.

A new derivative image and combined recovery map incorporated the chunk. Existing recovered overlaps had to agree; original acquisition artifacts were not patched. File coverage became **712 full, one partial and 345 unavailable**. The known DOOM2 directory now had all 15 files sector-covered. Whole-disc coverage still remained partial.

## Static package validation

The package was extracted from verified recovered extents into private staging. Every staged length/hash was compared with its image extents. Static inspection identified the DOS executable, WAD resources, configuration and support files. MZ and IWAD directory/map-record checks passed; 32 map markers were inspected. The known executable/resource pair was suitable for proposing an isolated DOS compatibility test.

Those checks were bounded structural checks, not an exhaustive dependency proof, proof of every map's behavior or authentication of the original publisher's exact release. Historical saves and optional multiplayer helpers were part of the known historical set; no permission to run them followed from extraction.

## Isolated compatibility tests

DOSBox-X loaded the executable, the DOS/4GW runtime and the WAD. An initial capture failure remained an inconclusive result. A separately authorized bounded-capture attempt observed engine initialization; that was not gameplay proof.

A graphical test used private authenticated Xvfb, Bubblewrap filesystem/network/device isolation, a disposable package, bounded output and an allowlisted keyboard/framebuffer relay. It reached the menu and difficulty selection but ended at the 150-second supervisor deadline. No fatal game error was established, and that attempt's incomplete result was preserved.

A later, separately authorized V2 session allowed a 600-second outer maximum, 570-second emulator deadline, 660 CPU seconds per process and 1 GiB address space per process. The human operator confirmed MAP01, movement, turning, firing and use, and later confirmed quitting through the game menu. The game returned to the DOS autoexec and DOSBox-X exited with code 0 after approximately 239 seconds. No deadline termination or forced kill occurred; preservation and process-cleanup checks passed.

## Remaining limits

- **Pause/resume:** the viewer recorded Fail. The operator clarified that P was tried without effect; Pause/Break was not confirmed. Future guidance was corrected; the historical result was preserved.
- **Audio:** disabled and untested.
- **Historical authenticity:** unverified; exact publisher release/build not authenticated.
- **Multiplayer:** the human could not confirm non-use. The retained complete execution log recorded no multiplayer utility execution; network initialization messages alone did not establish such execution.
- **Historical saves:** human non-use confirmation was unavailable; no historical-save file opens appeared in the retained log.
- **Visual corroboration:** first-menu and first-transition markers were not recorded. The saved frame was post-game emulator output, not a gameplay screenshot. The gameplay conclusion rests on scoped human confirmations.
- **Functional scope:** later levels, save/load, extended stability and the full game remain untested.

## Why a partial disc could support a working package

The relevant files' extents were concentrated in recovered regions. The missing executable could be acquired as one bounded target, so a small additional recovery completed the **known package set** even though most of the disc remained unrecovered. Disc-wide percentage did not determine this package's availability.

The supported conclusion is **human-verified limited interactive MAP01 play**, with explicit remaining limits. It is not complete functional validation, a historically authenticated release or authorization to redistribute the game. The repository's metadata fixture encodes recovery statistics and synthetic regression cases; it does not contain game data. See [workflow](../../WORKFLOW.md) and [schema](../../PRESERVATION_SCHEMA.md).

Product names identify historical software; no affiliation or endorsement is claimed.
