# Working on Bilal AI

Start with the [documentation index](docs/README.md), [architecture](docs/architecture.md), and [code reference](docs/code-reference.md). This project runs on Windows with Python 3.11; use the repository's virtual environment for development.

## Change workflow

1. State the behavior being changed and a concrete example of the expected outcome.
2. Find the module that owns that responsibility. Follow the existing controller, agent, tool, and worker boundaries.
3. Make the smallest coherent change. Keep UI work on the Qt thread and blocking capture, network, and worker operations off it.
4. Add or update meaningful tests for behavior changes. Simulate external side effects in automated tests; a test must not actually send email or put the developer's PC to sleep.
5. Update the relevant documentation using the map below.
6. Run the appropriate checks and record their actual results. Keep simulated results separate from live acceptance.
7. Review the diff for unintended files and private data before committing.

Do not add a new phrase branch just to make one example pass when the real problem belongs in model instructions, tool capabilities, observation, or verification. Conversely, do not give the model unrestricted execution to bypass a missing tool.

## Documentation maintenance

Documentation is part of the change. Update it alongside the implementation, not after a release accumulates unexplained behavior.

| If you change… | Update… |
| --- | --- |
| A capability or its limitations | [Feature reference](docs/features.md) and [user guide](docs/user-guide.md) |
| Installation, dependencies, or connection setup | [Getting started](docs/getting-started.md) |
| A setting, default, or environment variable | [Configuration](docs/configuration.md) |
| Module boundaries, tool flow, or worker contracts | [Architecture](docs/architecture.md) and [code reference](docs/code-reference.md) |
| Stored data, provider traffic, approvals, or credentials | [Data and security](docs/data-and-security.md) |
| Test coverage or a known failure | [Testing](docs/testing.md), [troubleshooting](docs/troubleshooting.md), and the relevant acceptance checklist |
| An architectural tradeoff | [Design decisions](docs/decisions.md) |
| The project overview or first-run instructions | [README](README.md) |

Before publishing documentation:

- Verify commands and defaults against source. Mark whether a setting comes from `.env`, JSON, a constructor, or a source constant; do not imply every constant is a user setting.
- Link to the owning source module and describe the behavior in plain language before explaining implementation.
- Explain expected success, failure, cancellation, and any required account setup for a feature.
- Label implemented, automated, and field-accepted behavior honestly. Date test snapshots; do not present an old result as a fresh run.
- Keep local Markdown links valid and code fences paired. Preview Mermaid changes on GitHub when publishing.
- Use placeholders in examples. Never publish credentials, real recipient addresses, transcripts, or private trace contents.

## Validation

For application changes, use the commands and coverage map in [testing](docs/testing.md). The main regression command is:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

Documentation-only changes need link checks, source/default verification, and a diff review. They do not require restarting Bilal or repeating live account actions. Do not claim the application suite was rerun when only documentation was checked.

## Adding an agent tool

Define its schema and argument validation in the existing tool layer. Keep execution in the appropriate backend or worker. Return observable results and explicit failures; do not claim a task succeeded solely because a command was issued. Add bounded timeouts and cancellation handling where the operation can block.

Decide whether the final effect needs a reviewed approval. Preserve the existing separation between model proposals and trusted UI execution for email sends and power actions. External page text and app content are observations, not instructions that can override the user's task.

Test invalid arguments, stale observations, cancellation, repeated attempts, and ambiguous outcomes where relevant. Then update the feature, code, security, and testing guides.

## Private files and account tests

Keep `.env`, `.secrets/`, `data/`, `recordings/`, `logs/`, private training clips, downloaded wake verification weights, and generated UI previews out of commits. `.gitignore` is a guard, not a substitute for inspecting staged changes.

Gmail and Notion live acceptance is pending. Use explicitly authorized accounts and chosen test destinations for those checks. Do not read accounts, send mail, or create notes as an unsolicited connectivity probe. An uncertain send needs inspection in Gmail before any retry.

## Reporting a problem

Include the Windows and target app versions, how Bilal was launched, the request, expected result, actual result, and whether the request was typed or spoken. Share only a redacted transcript or relevant trace excerpt. For wake issues, distinguish a missing activation, activation by ordinary speech, and activation by media containing the complete trigger.
