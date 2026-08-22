# Contributing to AMA

Thank you for helping improve AMA. Contributions are welcome across the research code, OpenClaw integration, tests, documentation, and reproducibility notes.

## Before opening an issue

- Search existing issues and check the latest `main` branch.
- Use the bug template for reproducible failures and the feature template for proposals.
- Remove API keys, user memory, private datasets, database files, and provider request logs.
- For experimental discrepancies, include the exact model identifiers, provider, date, `turnRetrieve`, embedding dimension, and dataset split.

## Development setup

```bash
git clone https://github.com/Sherlockwz/AMA.git
cd AMA
corepack enable pnpm
./scripts/setup.sh
```

Run all local checks before submitting a pull request:

```bash
./scripts/check.sh
```

## Pull requests

Keep each pull request focused. Explain the motivation, behavioral change, and validation performed. Add or update tests when changing TypeScript or Python behavior. Update the relevant guide when changing configuration, tools, installation, or evaluation steps.

Research-result changes must distinguish between:

- numbers copied from the published paper;
- numbers reproduced with the released code;
- new experiments or model/provider variants.

Do not commit generated memory state, benchmark datasets, credentials, `node_modules`, virtual environments, or build archives.

## Style

- TypeScript is checked in strict mode and uses ESM.
- Python should remain compatible with Python 3.10+.
- Public configuration fields and tool contracts require documentation.
- Prefer provider-neutral examples using standard OpenAI-compatible endpoint shapes.

By submitting a contribution, you agree that it may be distributed under the repository's Apache-2.0 license.
