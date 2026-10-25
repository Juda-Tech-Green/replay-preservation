# Public file manifest — v0.1.0-alpha

Exactly **68 files** are proposed for the first public commit. Names are enumerated in `public-release-files.json`. No Git repository/index/commit exists. Every file is original project source, public documentation/configuration or a synthetic/metadata-only fixture. Private trees and Git history were not copied.

All other file hashes are sealed below and checked by `scripts/audit_public_tree.py`. This document excludes its own size/hash to avoid self-reference; the final external audit hashes it too. Any edit requires renewed review and manifest generation.

| Proposed path | Bytes | SHA-256 | Review classification |
| --- | ---: | --- | --- |
| `.agents/skills/replay-preservation/SKILL.md` | 4773 | `9ff7f85c29b566b196c00806d7c92f259773f73754f60cf2cc0972469ecb2714` | Repository-local skill |
| `.agents/skills/replay-preservation/agents/openai.yaml` | 251 | `d76559fad04aac4ccf0564c5834b458fba8ffb1f2488b597b699a314f27e7801` | Repository-local skill |
| `.gitignore` | 456 | `c82d3e68306712d9e1a997bbff7a7ef1b1749490a41680614f04387d6c1f8920` | License/documentation/release configuration |
| `ARCHITECTURE.md` | 3394 | `95b0725591594c4ec87f6dac09a60abb2de04484fd8c4efa369025c1fa4f5f70` | License/documentation/release configuration |
| `CHANGELOG.md` | 1184 | `9cd1a129c94c9544e4b86c24f481b65310c9bdce0052a9b48f507bae1ba78e50` | License/documentation/release configuration |
| `CLI_REFERENCE.md` | 6771 | `f7979b6429b6c286dc74ea8e182580a0db1930496c3c86cd03ea16d249aa4468` | License/documentation/release configuration |
| `CONTRIBUTING.md` | 2767 | `045a08aa1b57d2f2e43df87f267446629e7f4d1e4b7d5888dd44d0e5d8919aa9` | License/documentation/release configuration |
| `DISC02_PILOT_PLAN.md` | 3638 | `4fca096fbb0f54bdcc0c18e1d97db9826965ebda9ed1774ef2bfe37c8fdcd631` | License/documentation/release configuration |
| `FIRST_PUSH_PLAN.md` | 2630 | `affee320f913d80c31ce6fa05b2814329ae08bb6ef2949557b4f35c5a7065d82` | License/documentation/release configuration |
| `LICENSE` | 1085 | `072bf3b08380d82cae9ffb0e08e6d9ded897ae9f3736c296fa572593de71f80c` | License/documentation/release configuration |
| `MANIFEST.in` | 806 | `de895ae0c1e1ee578a114106bbfc79007095144862146499734e9d7eda78f1ba` | License/documentation/release configuration |
| `PRESERVATION_SCHEMA.md` | 5260 | `6f7cb62d07f5a594cc33dd8b3ba98bcd52909b7e0bb8fa825d49ddf601255d7d` | License/documentation/release configuration |
| `PUBLIC_FILE_MANIFEST.md` | self | `excluded; externally hashed` | License/documentation/release configuration |
| `PUBLIC_RELEASE_READINESS.md` | 3748 | `56a81d4654d3ae4b0eeb94feedfc8d19ac0f647b997881f3f241772e50928ef9` | License/documentation/release configuration |
| `PUBLIC_SECURITY_AUDIT.md` | 5280 | `95a94996b3739a13cab084a3bd0a5dd1dbf12de0327b06d820ed38dde1cacdc5` | License/documentation/release configuration |
| `README.md` | 4620 | `88678a67c0ec180d356c3a3d77fc026051f7b3967a1c0ccb3c6dac279b2df982` | License/documentation/release configuration |
| `RELEASE_NOTES_v0.1.0-alpha.md` | 1336 | `474f7b833fafce70d9c590bc8a49339cd617231bda5514b9810fb298a21e13a3` | License/documentation/release configuration |
| `ROADMAP.md` | 1561 | `a104ee8d6f92c76917660b90102d8393a6a66e7c006672baf04d4a53f6884f8b` | License/documentation/release configuration |
| `SECURITY.md` | 2783 | `67fa14491e4b553b30660666c65d36664de8014474c48e282a17225bbf8f6e55` | License/documentation/release configuration |
| `SKILL.md` | 551 | `5fc9377f0c814cf42e83b2d754031c0531349d2542a76951a4d4466a8ffe1a21` | License/documentation/release configuration |
| `WORKFLOW.md` | 5177 | `5c8580c5d050c4d3ddb8f29dba72a6cfb54dbe5d7382a2bb72b8aaad9e008224` | License/documentation/release configuration |
| `docs/case-studies/disc-01-doom2.md` | 6466 | `096a8dcd86e8a2e7ea524911ce25d06c17e866e6357ed481f595581448d46512` | License/documentation/release configuration |
| `public-release-files.json` | 2661 | `b3dbeb99e2c44b4abfbd2aeea7defb15c0da81bc01512d0bdea5875f39c127e1` | License/documentation/release configuration |
| `pyproject.toml` | 1119 | `c008978f081215271779b82eb2b775d8eb1c651da90e190307b91195bef81c00` | License/documentation/release configuration |
| `requirements-build.txt` | 229 | `e0e40b89bc2964a4ec8083ef5d3c907a4f260f0897de2d63dd488173d4417f1f` | License/documentation/release configuration |
| `schemas/preservation-record-v0.1.schema.json` | 3485 | `82cac1bc4ee5b66ea52ee8c12f75509f6a44eec591030d0546573ba79aad400c` | Evidence schema |
| `scripts/audit_public_tree.py` | 5783 | `d08923a4d4fceddfa0deb8cee255660cc05ee984f769ae6959c7b18367f8e4b3` | CLI/build/static-audit helper |
| `scripts/build_public_release.py` | 2712 | `a89658eb8576d40439aa8443ef13bc73f20745d770c8cb6c247f62482df29bbd` | CLI/build/static-audit helper |
| `scripts/replay.py` | 199 | `3bb7fafe75e13cb31bc1ef91f528da3f4b075f87b2f5249a3031606b3053e305` | CLI/build/static-audit helper |
| `src/replay_preservation/__init__.py` | 78 | `41f15377b28423dd54b4153def00a73c3f1246bc0b7c26bd67317e4a8deda4e1` | Original project Python code |
| `src/replay_preservation/__main__.py` | 47 | `79ee6f134c5c5193377cf9b189cbdcc3e2095e49ba9cec310114441c15a917c4` | Original project Python code |
| `src/replay_preservation/archives.py` | 3671 | `fc443d682310925c97c676f8778cfc13cd58e0dc8007662edd02ab7031bd9a6e` | Original project Python code |
| `src/replay_preservation/assessment.py` | 23013 | `1de822c9437040579db227d17d76f57c8592da1e6378409fc6c3a22ee7cfceed` | Original project Python code |
| `src/replay_preservation/baseline.py` | 14250 | `3fd9b25b6d04095750c933007eea5e60c71f27356d53afb83084b777cd111485` | Original project Python code |
| `src/replay_preservation/bounded_process_capture.py` | 1901 | `6a7033c181e0f207ba37a061252359ea281bc0da4d6dfebd7a8972ae7ee6836b` | Original project Python code |
| `src/replay_preservation/candidates.py` | 10120 | `395ba9b0c60f1b6e5a0d6b2197723dd1014b7b72e0950fce5375662894e4619c` | Original project Python code |
| `src/replay_preservation/catalog.py` | 2632 | `62b42bee72ac6a65160faadc757ae3105ebddafcab9dccb6d63ba060fcbc1f04` | Original project Python code |
| `src/replay_preservation/cli.py` | 7140 | `b066bd7565cd97545883cea027648e6d0e8b18ae368f5dd24f67855b8642ad2a` | Original project Python code |
| `src/replay_preservation/compat/__init__.py` | 71 | `ab9bbcba56137cfa973f646d880e1d552f1835d624ad1a39e8962f9772be57b7` | Original project Python code |
| `src/replay_preservation/compat/private_display_protocol.py` | 3841 | `cb420438dc5245ab65ca9b823b55683450a1c0fa26982df950a7ca8d6f635663` | Original project Python code |
| `src/replay_preservation/compat/private_x11.py` | 5380 | `ecf71995b3a111e3f63342328c88a6fa51cf938bcbef1ca89f7c9b252ac80291` | Original project Python code |
| `src/replay_preservation/compat/viewer_state_v2.py` | 3059 | `97cae60dc50b62af81ff4086175f0ec7b65e6e8e96650fcd6d429682f4c68f19` | Original project Python code |
| `src/replay_preservation/compat/viewer_v2.py` | 18116 | `966a60157327e35f418e8de0c67d11fce5de4efae0daac36b13d13eadf1ed2aa` | Original project Python code |
| `src/replay_preservation/covered_components.py` | 2643 | `814a517b4e72e20aa20236dc2336700bce8eb4668d810f6d9a5318bde1082e85` | Original project Python code |
| `src/replay_preservation/doom_static.py` | 6778 | `fe65ef228eb0fcdf1163fb9560de2366635337f1bd1ccce463e5f1bcb1b48c7b` | Original project Python code |
| `src/replay_preservation/image_report.py` | 20060 | `5b930824898917b41af1b51d4f8f62a1baf64373bb0f40e6c670471ed6a2445d` | Original project Python code |
| `src/replay_preservation/iso_coverage.py` | 13588 | `36178c08712fbef9345e981ae6650dca8b98e138a7119912f81e1087bc850508` | Original project Python code |
| `src/replay_preservation/mapfile.py` | 2520 | `580c172b191e3a36d8c53396fca609d4a7eb74b44e279ecb9cc6a8536eb36bc6` | Original project Python code |
| `src/replay_preservation/preflight.py` | 3978 | `d1c6a4ef118af493c40b2c63ba817c8d80efbcc8959fe2ceae712daae622afca` | Original project Python code |
| `src/replay_preservation/signatures.py` | 3059 | `6e3804907b51639ce9ea8ec2fdf3288e9e0150bcc016476cceaab51d8cedfb69` | Original project Python code |
| `src/replay_preservation/target_merge.py` | 5076 | `39e4ae31334d0b68d9c7e6a77abcb548ab5cb3cedee44d26a8b1259d3df274c5` | Original project Python code |
| `src/replay_preservation/target_strategy.py` | 4202 | `5b62d445e3632cb6c0d6e90566a0a4c4567626f1ebf78312d37f097e35911f13` | Original project Python code |
| `templates/preservation_record.json` | 648 | `7c062dfeec4bcd6877aa7684d10bf1a3ee616dee23fe3db5d12b1ff7e835568a` | Non-executable template |
| `templates/supervised_session.json` | 1347 | `089b299a03007d5fc55f05993c387a10696aa3fe64ea2667c84a00feee96a604` | Non-executable template |
| `tests/fixtures/disc01_cases.json` | 1141 | `c7afe003619323e263dc13e1a45fbb5ed1ecf8a9def3f393138c1b805993f85e` | Metadata-only fixture |
| `tests/test_assessment.py` | 8107 | `ba66b9e15794847f663db34767d8fbfdda8193dc9a52adb6094a57d24dc9562e` | Synthetic regression |
| `tests/test_baseline.py` | 12792 | `cac647b7841e074db3ab23b5ced3e95174e6065e5230c30bfd51759e834b5401` | Synthetic regression |
| `tests/test_candidates.py` | 4410 | `3b93d4a7facfb6cb458978d29fab059c89248a2144bd5202132864cda066b759` | Synthetic regression |
| `tests/test_cli_commands.py` | 4019 | `65a2da589c20f055dd91a0844c67a90b7329bedd5bfe4a52003478ce464e6ae8` | Synthetic regression |
| `tests/test_covered_components.py` | 1738 | `a7a0f92d1e2d0f7b37c101c079b567b16a2ae0f79b33381e3e33e4397d39527a` | Synthetic regression |
| `tests/test_doom_static.py` | 1590 | `56507f0deac8b7a3a194d7ef3f6aa89f77d51fbf7771df6e638cac060a95fc08` | Synthetic regression |
| `tests/test_graphical_v2.py` | 3600 | `708c912a76b9c7f812858f93f9e4f31dec4f86dcbeb7497f280347dfe4993ddd` | Synthetic regression |
| `tests/test_iso_coverage.py` | 7243 | `619adf4adc9736b4386765d09ac43a5f3ddfcc8c61aece1e5c607169019daa39` | Synthetic regression |
| `tests/test_parsers.py` | 6441 | `76bd112f3db7f3dfbf3ac760773d3b987e2714e5b83cce29fea1ffc5c33a7ef2` | Synthetic regression |
| `tests/test_preflight.py` | 1958 | `2392c0f0d7f52449bc0c354d78ba4226c6cde2df549db3bb211488e787dfa27c` | Synthetic regression |
| `tests/test_public_release.py` | 4593 | `65d1282e9388f08b84c701338deffd063cdb1e457e31dd8c6e24854350cec288` | Synthetic regression |
| `tests/test_target_merge.py` | 2671 | `89f9b271da1cb82ccdc4c68c66df4f88ed2ded954fcd342686bdb971aefcb71c` | Synthetic regression |
| `tests/test_target_strategy.py` | 4561 | `4b219dd98ecb12437274f500fba487505cf0050ce6a31ce9763b5d1a35169293` | Synthetic regression |

Excluded: proprietary game binaries/resources/archives, original/derivative disc images, saved games, raw acquisition evidence, private catalogs/reports, historical execution approvals/controllers, credentials and private Git history. Generic Linux API/mock paths and historical game names are reviewed source text, not software payload.

Build environments, scanner logs and verification distributions remain outside this source tree. Proposed staged paths and the full staged diff must be reviewed after separately authorized Git initialization. This manifest does not claim a real index was already inspected.
