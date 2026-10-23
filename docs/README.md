# Bilal AI documentation

This is the guide to using, understanding, and developing Bilal AI. The source code is the implementation; these pages explain its behavior and the reasons behind it.

Reviewed against the repository on **23 October 2026**. Bilal is experimental. A feature being implemented does not mean it has passed real microphone, Windows sign-in, or connected-account acceptance tests.

## Current capability build

The runtime now includes a durable task queue, Task Center, exact local input slots, policy approvals, controlled files, credential settings, read-only headless delegation, an owned Chrome DOM session, and an explicit screen-question path. **This is a partial capability-spec implementation, not completion of every P0 requirement.** Read [Task system](task-system.md) for the active runtime and the [138-item capability matrix](CAPABILITY_STATUS.md) beside the [specification](CAPABILITY_SPEC.md) for evidence and gaps.

Wake is off by default behind independent acceptance. The normal talk chord is **left Ctrl + left Shift**; Settings supports remapping/toggle after restart, and **Ctrl+Alt+Backspace** is the global stop. Provider keys belong in Windows Credential Manager through Settings; Gemini/Groq migration/readback has been verified.

For multiple browsers and signed-in accounts, use [Give an existing window to Bilal](window-handoff.md). The desktop/tray entry opens explicit selection rather than guessing the account.

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
| [Task system](task-system.md) | How do queued tasks, exact input, policy, headless agents, and artifacts work now? |
| [Capability status](CAPABILITY_STATUS.md) | Which138 specification requirements are implemented, tested, partial, or pending? |
| [Architecture](architecture.md) | How do wake detection, recording, the model, tools, and UI work together? |
| [Code reference](code-reference.md) | Which module owns a responsibility, and where should I make a change? |
| [Configuration](configuration.md) | Which settings exist, where are their defaults, and how do I change them? |
| [Data and security](data-and-security.md) | What stays local, what goes to providers, and which actions require approval? |
| [Testing](testing.md) | Which checks are automated, and what still needs real-world validation? |
| [Troubleshooting](troubleshooting.md) | How do I investigate a failure without guessing? |
| [Design decisions](decisions.md) | Why does the implementation use this approach, and what tradeoffs remain? |
| [Contributing](../CONTRIBUTING.md) | How should code, tests, and documentation change together? |

See the [23 October native validation report](VALIDATION_2026-10-23.md) for bounded live checks and the latest running-app sample.

## Status and evidence

Use these terms consistently when discussing the project:

- **Implemented:** the behavior has a code path. This alone does not establish reliability.
- **Automated check:** a repeatable test covers specified behavior, often with simulated audio, model replies, or external effects.
- **Field acceptance:** a person checks the real microphone, speaker, Windows session, app, or account and records the outcome.
- **Pending:** the required acceptance evidence is missing. Do not infer a pass from a mock or from a credential file existing.

The capability build’s confirmed full native Windows snapshot is **195 passing tests in 22.078 seconds on 23 October 2026**. See [testing](testing.md) for its scope and wake replay evidence. Gmail and Notion live account acceptance remains pending; a connection inside Codex does not connect the standalone Bilal app.

## Historical and specialist references

These preserve implementation history or deeper specialist workflows. Use the guides above for the current explanation; check dated claims before relying on older reports.

- [MVP implementation report](MVP_IMPLEMENTATION.md): implementation milestones and validation evidence.
- [MVP baseline](MVP_BASELINE.md): the earlier starting point, not the current feature list.
- [Field acceptance checklist](FIELD_ACCEPTANCE.md): hands-on voice, startup, background playback, and account checks.
- [Wake calibration](../training/VOICE_CALIBRATION.md): specialist recording and scoring workflow.
- [Training overview](../training/README.md): training pipeline documentation.
- [Character asset notes](../assets/character/ASSET_NOTES.md): artwork provenance and animation constraints.

If code and documentation disagree, investigate the code and update the affected guide in the same change. See the [documentation maintenance checklist](../CONTRIBUTING.md#documentation-maintenance).
