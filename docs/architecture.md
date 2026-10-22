# Architecture

[Documentation home](README.md) · [Code reference](code-reference.md) · [Data and security](data-and-security.md)

Reviewed against the source on **22 October 2026**. This describes the current experimental implementation, not a promise of universal desktop control.

## What kind of system is Bilal?

Bilal is a Windows desktop **LLM agent with local tools**. Gemini interprets the user's goal and chooses structured tool calls. Python validates and executes those calls, returns observations, and lets the model decide the next step. The model does not directly control Windows and does not generate executable shell commands.

Separate models serve different purposes:

| Model | Job | Runs where |
| --- | --- | --- |
| Custom openWakeWord / ONNX classifier | Find likely wake phrase audio | Locally |
| Whisper base.en through faster-whisper | Check that a candidate contains the complete “Hey Bilal” phrase | Locally |
| Groq Whisper | Turn the recorded command into text | Hosted service |
| Gemini | Understand requests, choose tools, reason over results, answer | Hosted service |

The wake classifier is trained separately. Using an LLM agent does not mean Bilal continuously trains Gemini or modifies its own code.

## System map

```mermaid
flowchart TD
    Mic[Microphone] --> Wake[WakeMonitor: classifier and local phrase verifier]
    Wake --> Capture[Command capture using the same stream]
    Manual[Tray recording] --> Capture
    Capture --> STT[Groq transcription]
    STT --> Controller[AssistantController]
    Typed[Typed request or missing-detail reply] --> Controller
    Controller --> Router[RequestProcessor]
    Router --> Brain[AgentBrain.run]
    Brain --> Executor[AgentToolExecutor]
    Executor --> Desktop[Persistent desktop worker]
    Executor --> Media[Spotify worker and media readback]
    Executor --> Web[Chrome opening and public web reader]
    Executor --> Connectors[Gmail and Notion connectors]
    Executor --> State[SQLite preferences and pending approvals]
    Desktop --> Brain
    Media --> Brain
    Web --> Brain
    Connectors --> Brain
    Brain --> Controller
    Controller --> UI[Qt companion, dialogs and Windows speech]
    UI --> Approval[Human confirmation]
    Approval --> Workflow[BusinessWorkflows.resolve]
    Workflow --> State
```

Tools return evidence, errors, or pending work. A launch result with `verified: false` means the application opened; it does not prove the user's complete task succeeded.

## One voice request, end to end

1. `main.py` creates the Qt application, single-instance lock, controller, companion and tray. The companion starts hidden.
2. `WakeMonitor` reads 80 ms audio blocks. `DetectionGate` applies the acoustic threshold, consecutive-frame requirement and repeat cooldown.
3. A candidate includes recent audio plus short lookahead. `OfflineWakeVerifier` checks it in a background thread while the microphone continues buffering.
4. Only an accepted candidate produces a callback containing `phrase_verified=True`. The controller rejects stale, disabled or unverified callbacks.
5. Command capture reuses that microphone stream and buffered audio. It stops after configured silence, a user stop, or the maximum recording time.
6. The controller saves a local WAV and sends it to Groq. For wake-started requests, the final transcript must also contain “Hey Bilal”; otherwise agent execution is skipped. Typed/manual requests do not need that phrase.
7. `RequestProcessor.handle()` creates an executor and calls `AgentBrain.run()`.
8. The agent answers directly or performs the bounded observe–act–verify loop below.
9. The controller saves the answer for recorded requests and signals the Qt UI. The companion speaks through Windows speech and hides after completion. Wake monitoring resumes when the UI and request lifecycle allow it.

See [configuration](configuration.md) for the current audio and wake constants. The phrase verifier is context-biased: it receives `Hey Bilal.` as vocabulary context and additionally requires the full phrase, average log probability at least `-0.49`, and no-speech probability below `0.6`. It is neither speaker identification nor playback echo cancellation.

## The agent loop

`AgentBrain.run(query, executor, ...)` supplies Gemini with the active request, recent conversation, confirmed preferences, current Asia/Karachi date, agent rules and declared tools. The default retains six request/answer pairs in memory.

Each round:

1. Check cancellation and the overall deadline.
2. Ask Gemini for an answer or function calls, with automatic SDK function execution disabled.
3. Validate each requested tool and its arguments in `AgentToolExecutor`.
4. Execute at most one mutating tool in that model turn; return an error for another mutation in the same turn.
5. Return actual tool results to Gemini, preserving the provider's original response content and thought signatures.
6. Continue until an answer, clarification, power confirmation, error, cancellation, or limit.

Default bounds are **12 rounds**, an overall **180-second budget**, and **20-second model HTTP timeout**. The overall deadline is checked between rounds; it is not a hard interrupt of every in-progress operation. Worker/API timeouts also apply.

A tool result with `outcome_uncertain` prevents subsequent mutations during that run. For example, a network timeout after creating a note must not silently create duplicates.

## Observe before acting

The generic desktop worker keeps Windows accessibility handles in one process for a request. The agent receives opaque IDs instead of raw handles:

- `list_apps` returns registered application IDs; `launch_app` accepts only a discovered ID.
- `list_windows` returns window IDs and invalidates prior control observations.
- `inspect_window` returns fresh control IDs, labels, types and available values.
- `activate_control` invokes an observed button/link/menu/tab; `enter_text` sets an observed edit/combo value literally.
- Each generic mutation invalidates control IDs, including a failed invocation. The model must inspect again.

This architecture avoids guessing screen coordinates, but depends on applications exposing usable accessibility controls. There is no screenshot reasoning or browser DOM driver. The dedicated Spotify workflow adds domain-specific search and playback verification.

## Clarification is a pause, not a new task

The model calls `request_input(question, field)` when a detail is missing. The loop prioritizes that call before other calls in the same response and returns the question. The controller retains a pending input record and pauses wake activation. The UI opens a temporary email/text field.

On submission, local validation runs and the answer continues through the agent with previous task context. Completed tool progress is included when clarification follows earlier work. Pasting an email address never approves sending. Cancellation discards the pending input and records the cancellation in conversation context.

## Human approvals use a separate execution path

Email sending, saved preferences and system power actions create records in `LocalState`. The model has proposal tools, but no approve, send or execute-power tool.

The Qt UI shows the actual pending payload. A user decision calls `BusinessWorkflows.resolve(action_id, fingerprint, approve)`. SQLite atomically claims that exact pending action once. Changed email content creates a replacement approval; expired power confirmations fail. On startup, an action left `executing` becomes `uncertain` rather than replaying.

See [data and security](data-and-security.md) for the approval lifecycle and limits.

## Threads and processes

| Component | Execution model | Why |
| --- | --- | --- |
| Qt widgets, painting and dialogs | Main GUI thread | Keep Qt object access and painting in its event loop |
| Recording, transcription, agent work | Background threads | Keep the companion responsive; report via Qt signals |
| Wake microphone loop | Dedicated daemon thread | Continuously read audio without blocking the UI |
| Offline wake verification | Bounded background inference | Keep audio buffering while verification runs |
| Desktop automation | JSON-line subprocess per executor | Keep COM/UI handles together and allow timeout/cancellation cleanup |
| Spotify automation | Dedicated subprocess | Isolate app/media automation |
| Offline cancel listener | Trusted Windows speech helper | Hear cancellation while transcription or agent work runs |
| Guided wake collection | Interactive subprocess started by user | Review and label recordings explicitly |

`runtime_paths.worker_python()` chooses `python.exe` for workers even when startup uses `pythonw.exe`. Worker windows are hidden except the explicitly requested recording/labeling console. Cancellation stops future steps and kills relevant workers; it cannot undo completed external actions.

## Startup and shutdown

`startup_windows.py` installs a current-user sign-in shortcut to `launch_bilal.pyw`. It uses the Windows-known Startup folder API rather than a hardcoded path. The launcher redirects background output and starts the normal Qt app. `QLockFile` prevents duplicate instances.

A SIGINT handler requests shutdown through an event; the Qt timer performs cleanup. Painter resources use explicit cleanup, and timers, speech and background listeners are stopped during exit. Startup is after user sign-in, not a system service before login.

## Current boundaries

Implemented does not mean accepted in every environment. Live Gmail/Notion account acceptance, physical startup/power checks, and fresh background-video/voice testing remain separate acceptance work. The historical automated snapshot is 123 passing tests on 21 October 2026; it is not evidence of live delivery or universal app compatibility. Follow [testing](testing.md) and the [field acceptance guide](FIELD_ACCEPTANCE.md).
