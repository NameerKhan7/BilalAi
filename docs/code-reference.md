# Code reference

[Documentation home](README.md) · [Architecture](architecture.md) · [Testing](testing.md)

Reviewed **23 October 2026**. Paths below are relative to the repository root. Follow the runtime from `main.py` rather than treating every file as an active subsystem.

## Start reading here

1. [`ui_controller.py`](../ui_controller.py): how a user request changes state.
2. [`request_router.py`](../request_router.py): the small handoff to the agent.
3. [`agent_core.py`](../agent_core.py): model context, tool loop and exit conditions.
4. [`agent_tools.py`](../agent_tools.py): what the model can request and how calls are checked.
5. The worker or connector for the feature you want to change.
6. The related tests before editing behavior.

## Interface and lifecycle

| File | Main interfaces | Responsibility |
| --- | --- | --- |
| [`main.py`](../main.py) | `main()`, `AssistantWindow`, `CharacterStage`, `VoiceWave`, `managed_painter()` | Qt application, tray, tiny character/orb, speech, dialogs, animation, runtime status and graceful exit |
| [`ui_controller.py`](../ui_controller.py) | `AssistantController`, `event` signal, `record()`, `send()`, `submit_input()`, `resolve_approval()`, `cancel_request()`, `close()` | Background task orchestration and lifecycle state |
| [`conversation.py`](../conversation.py) | `ConversationSession`, `FOLLOWUP_WAIT_SECONDS`, `is_conversation_end()` | Session presence, 15s follow-up wait, and exact whole-utterance endings |
| [`hold_to_talk.py`](../hold_to_talk.py) | `HoldToTalk`, `changed` signal, `poll()` | Global left Ctrl + left Shift state polling and held/released transitions; no typing log |
| [`contextual_input.py`](../contextual_input.py) | `ContextInputDialog`, `validate_detail()` | Temporary missing-detail dialog and local validation |
| [`launch_bilal.pyw`](../launch_bilal.pyw) | Launcher entry point | Hidden startup, output redirection and Qt logging |
| [`startup_windows.py`](../startup_windows.py) | `shortcut_path()`, `configure()` | Install/remove and verify current-user startup shortcut |
| [`runtime_paths.py`](../runtime_paths.py) | `worker_python()` | Locate the console interpreter for worker subprocesses |
| [`brand_theme.json`](../brand_theme.json) | Theme data | UI colors, typography and companion layout settings |

The controller's main states are `idle`, `recording`, `transcribing`, `thinking`, `learning` and `approval`. A pending contextual input, conversation-active flag, capture mode, and thread-safe hold event are tracked separately. `AssistantWindow.begin_conversation()`, `continue_conversation()`, `end_conversation()`, and `hold_changed()` govern presence and follow-up capture independently of model turns. UI events include progress, transcript, reply, input, approval, error and finished signals. Visual poses are presentation states; they are not the same as controller task states.

## Reasoning and tool boundary

| File | Main interfaces | Responsibility |
| --- | --- | --- |
| [`request_router.py`](../request_router.py) | `RequestProcessor.handle()`, `RequestCancelled` | Create executor, call `brain.run()`, retain trace, return `RequestResult` |
| [`agent_core.py`](../agent_core.py) | `AgentBrain.run()`, `remember()`, `clear()`, `AgentError` | Manual Gemini function loop, conversation, confirmed preferences, date context, limits and trace persistence |
| [`agent_tools.py`](../agent_tools.py) | `TOOL_DECLARATIONS`, `AgentToolExecutor.execute()`, `DesktopBridge.call()` | Typed tool contract, validation, dispatch and desktop worker transport |
| [`command_types.py`](../command_types.py) | `CommandDecision`, `RequestResult` | Validated supported-browser request and result data types |

`AgentBrain.ask()` and `SYSTEM_PROMPT` are an older text-answer interface retained in the module. The desktop request path uses **`run()` and `AGENT_PROMPT`**. Editing only the older prompt will not update the agent's active behavior.

### Model-visible tools

| Group | Tool names | Important result meaning |
| --- | --- | --- |
| Clarification | `request_input` | Pauses for a non-secret email/text detail |
| Desktop discovery | `list_apps`, `list_windows`, `inspect_window` | Returns observed IDs and current accessible state |
| Desktop action | `launch_app`, `activate_control`, `enter_text` | Usually unverified until a fresh observation |
| Music | `spotify_play`, `media_status` | Dedicated playback operation and actual media readback |
| Browser and web | `browser_search`, `open_site`, `open_url`, `read_webpage` | Opening differs from reading or finishing a task |
| Accounts | `gmail_create_draft`, `notion_search`, `notion_read`, `notion_create_note` | Gmail draft is unsent; Notion creation includes readback |
| Proposals | `propose_memory`, `request_system_power` | Human confirmation required before saving/executing |

All declared parameters are strings; enums constrain selected fields. Dispatch rejects unknown tools, extra/missing fields, non-string values and values longer than 4,000 characters. Feature-specific validators impose additional limits. There is deliberately no model tool for arbitrary shell execution, approval or email sending.

## Desktop, browser and media

| File | Main interfaces | Responsibility |
| --- | --- | --- |
| [`desktop_worker.py`](../desktop_worker.py) | `DesktopSession`, `execute()`, `main()` | UI Automation discovery, control inspection, literal text entry, restricted invocation and media status |
| [`app_tools.py`](../app_tools.py) | `open_app()`, `store_catalog()`, `AppLaunchError` | Older supported executable/Store launch helpers; `AppLaunchError` remains used by active error handling |
| [`browser_tools.py`](../browser_tools.py) | `BrowserTools.open_url()`, `execute()`, `find_chrome()`, `search_url()` | Chrome discovery and opening supported searches/HTTP(S) pages |
| [`web_reader.py`](../web_reader.py) | `read_webpage()`, `validate_url()` | Bounded public page text retrieval and destination validation |
| [`spotify_tools.py`](../spotify_tools.py) | `play_spotify()` | Start and supervise the Spotify workflow subprocess |
| [`spotify_worker.py`](../spotify_worker.py) | Worker entry point, `media_snapshot()`, `process_name()` | Spotify accessibility interaction and Windows media-session evidence |

`app_tools.open_app()` is not the generic agent launcher: that path uses `DesktopSession.launch_app()`. Do not mistake its older three-app helper list for the agent's discovery coverage.

`DesktopBridge` sends one JSON object per stdin line with `tool` and `args`; the worker writes one result object per stdout line. Handles remain in the worker. Treat IDs as temporary observation references, not persistent identifiers.

## Voice pipeline

| File | Main interfaces | Responsibility |
| --- | --- | --- |
| [`wakeword.py`](../wakeword.py) | `load_settings()`, `load_detector()`, `score_wav()` | Shared classifier loading/scoring and diagnostic CLI |
| [`wakeword_gate.py`](../wakeword_gate.py) | `DetectionGate` | Threshold, consecutive frames, cooldown and rearming |
| [`wake_service.py`](../wake_service.py) | `WakeMonitor` | Persistent wake microphone loop, buffering, verification handoff and retry |
| [`wake_verifier.py`](../wake_verifier.py) | `OfflineWakeVerifier`, `command_after_wake()` | Local Whisper phrase check and final transcript trigger extraction |
| [`audio_capture.py`](../audio_capture.py) | `CaptureConfig`, `CaptureResult`, `CommandEndpoint`, `capture_command()`, `save_recording()` | Audio endpoint logic with held-state suppression of silence/no-speech endpoints, bounded stream capture and WAV serialization |
| [`stt_client.py`](../stt_client.py) | `transcribe_recording()`, `TranscriptionError` | Groq command transcription with bounded requests and vocabulary context |
| [`voice_cancel.py`](../voice_cancel.py) | `CancelListener`, `is_cancel_request()`, `strip_wake_prefix()` | Offline cancellation recognition and full-utterance cancellation handling |
| [`setup_wake_verifier.py`](../setup_wake_verifier.py) | Installer CLI | Download pinned public verifier model and verify weight integrity |

Do not conflate the two Whisper uses: the wake verifier stays local; complete command transcription goes to Groq. The baseline classifier is `models/hey_bilal.onnx`; downloaded verifier files live separately in ignored `models/wake_asr/`.

## Accounts, persistence and approvals

| File | Main interfaces | Responsibility |
| --- | --- | --- |
| [`business_tools.py`](../business_tools.py) | `GmailClient`, `NotionClient`, `BusinessWorkflows`, `canonical_email()` | Connector API calls, draft snapshots, readback and approval resolution |
| [`memory.py`](../memory.py) | `LocalState`, `digest()` | SQLite memories and one-time, payload-bound approval records |
| [`secret_store.py`](../secret_store.py) | `save_secret()`, `load_secret()`, `path_for()` | Windows-user-bound DPAPI storage for Gmail/Notion credentials |
| [`setup_connections.py`](../setup_connections.py) | Setup CLI | Explicit standalone Gmail OAuth / Notion integration setup |
| [`power_tools.py`](../power_tools.py) | `PowerActions`, `WindowsPower`, `suspend_windows()` | Propose expiring power approval and execute fixed Windows actions only after resolution |

Constructor injection (`state`, sessions, desktop bridge, Spotify player or power backend) lets tests use fakes without sending email or changing PC power. Preserve these seams when refactoring.

## Reviewed learning and diagnostics

| File or directory | Role |
| --- | --- |
| [`wake_learning.py`](../wake_learning.py) | Store candidates, explicit labels, hashes and reviewed-data checks |
| [`collect_wake_examples.py`](../collect_wake_examples.py) | Guided local collection and playback before confirmation |
| [`evaluate_wake_learning.py`](../evaluate_wake_learning.py) | Evaluate reviewed examples under deployed settings; report, do not change the model |
| [`train_reviewed_wake.py`](../train_reviewed_wake.py) | Gate training on reviewed sessions, prepare private candidate inputs and optionally train |
| [`training/train_personalized.py`](../training/train_personalized.py) | Candidate training with session-held-out evaluation |
| [`calibrate_wakeword.py`](../calibrate_wakeword.py) | Diagnostic recording/scoring workflow |
| [`check_mvp_readiness.py`](../check_mvp_readiness.py) | Local readiness report and optional test run |
| [`tests/`](../tests/) | Unit/contract tests and simulated integration scenarios |

Learning means confirmed preferences and reviewed candidate training. No automatic model promotion, Gemini fine-tuning or autonomous self-modifying code is implemented.

## Placeholder and historical material

`supervisor.py`, `tray.py`, `tts.py` and `skill_loader.py` currently contain no implementation. Do not build an architecture explanation around their filenames. Tray and speech behavior live in `main.py`; request supervision lives in `ui_controller.py` and `agent_core.py`. Likewise, a roadmap describes intended work and is not proof of implementation.

## Where a change usually belongs

| Desired change | Start in | Then review |
| --- | --- | --- |
| Hold-to-talk or follow-up timing | `hold_to_talk.py`, `conversation.py`, `main.py`, `ui_controller.py`, `audio_capture.py` | Endpoint, presence, modifier release, and microphone lifecycle tests |
| Wake false-positive handling | `wake_service.py`, `wake_verifier.py`, `wakeword_gate.py` | Wake activation tests and fresh field recordings |
| Agent picks the wrong task | `agent_core.py` active prompt/loop | Agent-loop tests and actual tool evidence |
| New local capability | `agent_tools.py` plus dedicated backend | Validation, verification, cancellation and approvals |
| App controls are stale | `desktop_worker.py` | Observation invalidation and desktop tests |
| Missing address/input behavior | `contextual_input.py`, `ui_controller.py` | Context retention and no implicit send approval |
| Email send safety | `business_tools.py`, `memory.py` | Exact content review, atomic claim and uncertain-outcome cases |
| Companion layout/animation | `main.py`, `brand_theme.json` | Preview renders and shutdown painting tests |

Use [testing](testing.md) to choose checks for a change and [data and security](data-and-security.md) before extending account or desktop privileges.
