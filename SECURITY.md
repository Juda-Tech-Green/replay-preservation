# Security policy

This alpha processes untrusted historical file formats. Parser bounds and tests reduce some risks; they do not certify arbitrary input safe or authenticate a publisher's original release. Work on private verified copies in a directory without concurrent hostile writers. Apply appropriate OS resource limits before processing large or hostile archives/images.

The offline CLI rejects devices, symlink components and files on iso9660/udf mounts. It verifies supplied hashes before image/chunk operations and rechecks input hashes afterward. It creates fresh derivative/extraction directories; failed operations retain explicit failure state. These path checks assume stable local inputs and do not claim race-proof access against a malicious concurrent process. Sparse inspection requires filesystem support. SHA-256 alone does not establish authenticity.

The Python library also includes lower-level mounted-assessment and catalog-writing functions for developers. They are not equivalent to the guarded offline CLI. Do not call them on physical media without authorization or on evidence destinations that must remain immutable.

Experimental `compat` helpers implement viewer state and a fixed framebuffer/allowlisted keyboard protocol. They are not a sandbox. The public release excludes the private Bubblewrap/Xvfb session controllers, evidence paths, authorization files and recovered package. No helper should be treated as a safe general game launcher or pointed at a host desktop on that assumption. No recovered execution is part of installation or testing.

Never commit game files, disc images, save files, private databases, acquisition logs, secrets or personal paths. The release audit checks an explicit proposed file set rather than relying on `.gitignore`. Custom static scanners and signature/extension checks cannot prove the absence of every secret, encoded payload, license problem or vulnerability; human review remains required.

## Reporting a vulnerability

Do not publish a secret or proprietary payload in a public issue. Use the repository's private vulnerability reporting mechanism **if the maintainers have enabled it**. No private reporting endpoint has been confirmed for this initial candidate. If none is available, open a minimal issue requesting a private contact without exploit details, sensitive logs or attachments.

Version 0.1.0-alpha is the initial review candidate. There is no established support window or security response SLA. Maintainers should acknowledge, reproduce using synthetic inputs, patch with regression coverage and describe affected versions before announcing a fix. Report discovered limitations honestly; do not label the project audited or vulnerability-free based solely on these release checks.
