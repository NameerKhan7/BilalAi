# Bilal AI documentation

This is the guide to using, understanding, and developing Bilal AI. The source code is the implementation; these pages explain its behavior and the reasons behind it.

Reviewed against the repository on **23 October 2026**. Bilal is experimental. A feature being implemented does not mean it has passed real microphone, Windows sign-in, or connected-account acceptance tests.

## Start here

| Your goal | Read in this order |
| --- | --- |
| Install and use Bilal | [Getting started](getting-started.md) → [User guide](user-guide.md) → [Troubleshooting](troubleshooting.md) |
| Understand what each feature does | [Feature reference](features.md) → [Configuration](configuration.md) |
| Understand how the code works | [Architecture](architecture.md) → [Code reference](code-reference.md) → [Design decisions](decisions.md) |
| Change or extend Bilal | [Contributing](../CONTRIBUTING.md) → [Code reference](code-reference.md) → [Testing](testing.md) |
| Understand accounts, approvals, and saved data | [Data and security](data-and-security.md) |
| Assess release readiness | [Testing](testing.md) → [Field acceptance checklist](FIELD_ACCEPTANCE.md) |

## Documentation map

| Guide | What it answers |
| --- | --- |
| [Getting started](getting-started.md) | What do I install, configure, and run? |
| [User guide](user-guide.md) | How do I talk to Bilal, type missing details, cancel, and review actions? |
| [Feature reference](features.md) | What can each feature do, what are its limits, and where is its code? |
| [Architecture](architecture.md) | How do wake detection, recording, the model, tools, and UI work together? |
| [Code reference](code-reference.md) | Which module owns a responsibility, and where should I make a change? |
| [Configuration](configuration.md) | Which settings exist, where are their defaults, and how do I change them? |
| [Data and security](data-and-security.md) | What stays local, what goes to providers, and which actions require approval? |
| [Testing](testing.md) | Which checks are automated, and what still needs real-world validation? |
| [Troubleshooting](troubleshooting.md) | How do I investigate a failure without guessing? |
| [Design decisions](decisions.md) | Why does the implementation use this approach, and what tradeoffs remain? |
| [Contributing](../CONTRIBUTING.md) | How should code, tests, and documentation change together? |

## Status and evidence

Use these terms consistently when discussing the project:

- **Implemented:** the behavior has a code path. This alone does not establish reliability.
- **Automated check:** a repeatable test covers specified behavior, often with simulated audio, model replies, or external effects.
- **Field acceptance:** a person checks the real microphone, speaker, Windows session, app, or account and records the outcome.
- **Pending:** the required acceptance evidence is missing. Do not infer a pass from a mock or from a credential file existing.

The latest recorded regression snapshot is **154 passing automated tests on 23 October 2026**. See [testing](testing.md) for its scope and wake replay evidence. Gmail and Notion live account acceptance remains pending; a connection inside Codex does not connect the standalone Bilal app.

## Historical and specialist references

These preserve implementation history or deeper specialist workflows. Use the guides above for the current explanation; check dated claims before relying on older reports.

- [MVP implementation report](MVP_IMPLEMENTATION.md): implementation milestones and validation evidence.
- [MVP baseline](MVP_BASELINE.md): the earlier starting point, not the current feature list.
- [Field acceptance checklist](FIELD_ACCEPTANCE.md): hands-on voice, startup, background playback, and account checks.
- [Wake calibration](../training/VOICE_CALIBRATION.md): specialist recording and scoring workflow.
- [Training overview](../training/README.md): training pipeline documentation.
- [Character asset notes](../assets/character/ASSET_NOTES.md): artwork provenance and animation constraints.

If code and documentation disagree, investigate the code and update the affected guide in the same change. See the [documentation maintenance checklist](../CONTRIBUTING.md#documentation-maintenance).
