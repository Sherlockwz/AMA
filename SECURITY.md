# Security policy

## Supported versions

Security fixes are applied to the latest release and the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability involving credential exposure, arbitrary code execution, path traversal, memory isolation, or unauthorized deletion. Use GitHub's private vulnerability reporting feature on this repository instead.

Include the affected version or commit, impact, minimal reproduction, and any suggested mitigation. Remove real API keys, user conversations, and provider logs before submitting the report.

## Deployment notes

- Run the sidecar on loopback (`127.0.0.1`) and do not expose port 8321 directly to untrusted networks.
- Keep provider keys in environment variables or OpenClaw secret references.
- Treat plugins as executable code and pin a reviewed release or commit in production.
- Keep `dataDir` private; it may contain conversation-derived facts, episodes, and vector indices.
- Back up runtime data before using memory deletion or migration operations.
