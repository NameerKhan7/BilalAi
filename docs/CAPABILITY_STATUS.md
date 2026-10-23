# Capability implementation and acceptance status

[Documentation home](README.md) · [Full capability spec](CAPABILITY_SPEC.md) · [Machine-readable matrix](capabilities.json) · [Testing](testing.md)

Reviewed **23 October 2026**. All **138 capability IDs** remain tracked, including future P2/P3 scope. Current code includes durable background tasks, policy and exact-step approvals, literal slots, allowed file tools, headless adapters, owned Chrome DOM, media/volume controls, project profiles and user-selected screen questions/pointer capture. **v1 and all P0 capabilities are not complete.**

## What the evidence proves

The latest confirmed full regression is **195 passing tests in 22.078 seconds on native Windows**, including screen/DOM and deterministic batch/restart/approval-revocation tests. Automated results include simulations and cannot establish physical screen/microphone or live work-account acceptance.

| Native evidence, 23 October 2026 | What passed | What it does not prove |
| --- | --- | --- |
| Gemini task | One queued provider-backed answer succeeded | 50-command benchmark or all-task reliability |
| Codex adapter | Real read-only invocation returned final answer and usage | Approved writes, project-only read isolation or 20 handoffs |
| Claude runtime | Official 2.1.309 installed; version/bare-mode flags checked | Live invocation; Anthropic key is missing |
| Keyboard hook | Native register/release succeeded | 50 trials/mode, remapping, full-screen/elevated acceptance |
| Owned Chrome | Open/read verified on example.com, www.python.org, docs.python.org, en.wikipedia.org, www.wikipedia.org | Five-site form filling/click workflows |
| Clipboard | Native 100000-byte text roundtrip passed and original clipboard restored | File/image clipboard or other app workflows |
| Credential storage | Gemini/Groq keys migrated and readback-verified in Windows Credential Manager | Complete secret scan or all providers/accounts |

Screen picker/indicator, memory-only frames, sensitive-window blocklist, pointer interception/cropping/drag and 20 screen questions/day limit are implemented. **No real screenshot or 20-element pointer accuracy acceptance was performed.** UIA grounding exists; local OCR does not. Wake defaults off until independent acceptance evidence satisfies its gate. Pending non-secret deterministic plans survive restart for explicit review/resume; secret slots require a fresh paste. See [task-system details](task-system.md).

| Tier | Meaning | Capability count |
| --- | --- | --- |
| P0 | Required before v1 ships | 51 |
| P1 | Next release | 51 |
| P2 | Good to have; explicit future scope | 31 |
| P3 | Later or possibly never | 5 |

## Status rules

| Status | Meaning |
| --- | --- |
| `planned` | No complete implementation assessed against this capability; future rows remain explicit. |
| `partial` | Some related implementation exists; the capability or acceptance is incomplete. |
| `implemented-with-evidence` | Reviewed source/evidence supports the stated baseline scope; separate acceptance cases can still be pending. |
| `acceptance-pending` | Core implementation exists; specified real-world acceptance is not passed. |

Each capability has case `AC-<ID>` in JSON. Most full-spec cases remain unrun. AGT-2 records a bounded native prompt-in/final-answer-out pass; CTL-3 records a native 100000-byte text clipboard pass. Neither closes broader delegation/write/isolation or application-workflow gates. Original baseline notes remain available alongside current implementation notes.

## Remaining completeness blockers

- Full 50-command benchmark, fresh voice/STT/hotkey trials, 1 hour wake negatives, seven-day dogfooding, 20 consecutive handoffs and fresh install acceptance remain pending.
- Claude awaits an Anthropic API key/live acceptance. Neither adapter exposes approved write execution or establishes OS project-only read isolation.
- Editable batch review now supports up to 20 deterministic file/contact/project/schedule calls with one approval, invalidated consent after edits and a no-replay step cursor. Dynamic UI batches and external-agent plan-to-write execution remain incomplete.
- DOM navigation/read works on five sites; cross-site form workflows, risky submissions and existing personal Chrome-profile workflows remain outside that proof.
- Physical capture/indicator/privacy/pointing acceptance, screen-answer accuracy, local OCR and mixed-DPI/exclusive-fullscreen coverage remain incomplete.
- File/domain allowlists exist; full app/recipient policy, exhaustive secrets/egress coverage and complete audit reconstruction need further work.
- Installer/onboarding, licensing review, live Gmail/Notion/calendar, real startup/resource measurements and broad app compatibility remain release work.

## Traceability matrix

Evidence paths identify implementation/contract scope; native results are separately bounded above and in JSON.

### VOI

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| VOI-1 / AC-VOI-1 | P0 | Push-to-talk activation | acceptance-pending | [hold_to_talk.py](../hold_to_talk.py), [main.py](../main.py), [task_center.py](../task_center.py), [test_conversation.py](../tests/test_conversation.py) | Hook-based global talk activation defaults to Ctrl+Shift+Space; settings persist remapped chords/hold-toggle mode (restart to apply). No 50-trial physical activation result. |
| VOI-2 / AC-VOI-2 | P0 | Speech to text | partial | [provider_interfaces.py](../provider_interfaces.py), [ui_controller.py](../ui_controller.py), [stt_client.py](../stt_client.py), [test_stt_client.py](../tests/test_stt_client.py) | Transcriber protocol and Groq adapter are used by task-enabled voice capture; vocabulary remains supported. Fifty independently spoken commands and 90% accuracy gate are pending. |
| VOI-3 / AC-VOI-3 | P0 | Multi-command utterances | acceptance-pending | [provider_interfaces.py](../provider_interfaces.py), [task_engine.py](../task_engine.py), [task_runtime.py](../task_runtime.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Structured Gemini planner can split up to eight intents into persisted independent child tasks. Mock-planner tests cover three intents/dependencies; live semantic splitting benchmark remains pending. |
| VOI-4 / AC-VOI-4 | P0 | Interrupt and cancel | partial | [voice_cancel.py](../voice_cancel.py), [ui_controller.py](../ui_controller.py), [main.py](../main.py), [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [test_conversation.py](../tests/test_conversation.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Current-request and named/latest background cancellation plus speech stop are connected. Cancellation is cooperative at boundaries; under-one-second physical stop is unmeasured. |
| VOI-5 / AC-VOI-5 | P0 | Spoken status and confirmations | partial | [main.py](../main.py), [test_conversation.py](../tests/test_conversation.py) | Background completion speech is shortened when over 15 words. Other reply/approval paths still need routine-response length and interruption acceptance. |
| VOI-6 / AC-VOI-6 | P0 | Status queries | implemented-with-evidence | [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [capability_tools.py](../capability_tools.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Status command patterns and task_status return states from the durable task store; foundation contracts exercise store-backed status. Named-provider conversational status still depends on reasoning. |
| VOI-7 / AC-VOI-7 | P0 | Text input fallback | implemented-with-evidence | [main.py](../main.py), [ui_controller.py](../ui_controller.py), [test_ui_controller.py](../tests/test_ui_controller.py) | Typed requests use the same controller/agent path as transcribed requests; this establishes the baseline fallback, not later literal or task-engine features. |
| VOI-8 / AC-VOI-8 | P1 | Wake word "Hey Bilal" | acceptance-pending | [wake_acceptance.py](../wake_acceptance.py), [ui_controller.py](../ui_controller.py), [wake_service.py](../wake_service.py), [wake_verifier.py](../wake_verifier.py), [test_wake_activation.py](../tests/test_wake_activation.py) | Wake defaults off in production until a fresh independent report meets >=50 positive trials, >=90% true activation, >=3600 negative seconds, <1 false activation/hour and <=30-day age. Physical evidence is not yet supplied. |
| VOI-9 / AC-VOI-9 | P1 | Clarifying questions | partial | [contextual_input.py](../contextual_input.py), [ui_controller.py](../ui_controller.py), [test_contextual_input.py](../tests/test_contextual_input.py), [test_conversation.py](../tests/test_conversation.py) | Contextual clarification and spoken follow-up support exist; at-most-one question across an entire command is not guaranteed. |
| VOI-10 / AC-VOI-10 | P1 | Conversation context | partial | [task_store.py](../task_store.py), [task_runtime.py](../task_runtime.py), [agent_core.py](../agent_core.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Recent turns now persist and reload through TaskStore. Ten scripted referential follow-ups and ambiguous-recipient behavior remain unaccepted. |
| VOI-11 / AC-VOI-11 | P2 | Urdu and Roman Urdu commands | planned | — | Natural language matching is not an Urdu STT accuracy benchmark; no WER claim is justified. |
| VOI-12 / AC-VOI-12 | P2 | Voice dictation mode | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| VOI-13 / AC-VOI-13 | P3 | Voice identity (only respond to the owner) | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### TSK

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| TSK-1 / AC-TSK-1 | P0 | Task objects | implemented-with-evidence | [task_store.py](../task_store.py), [task_engine.py](../task_engine.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | SQLite task IDs/goals/owners/plans/states/timestamps/results, task_steps and artifacts are implemented. Contract tests cover persistence and terminal-state behavior. |
| TSK-2 / AC-TSK-2 | P0 | Background execution | acceptance-pending | [task_engine.py](../task_engine.py), [task_runtime.py](../task_runtime.py), [ui_controller.py](../ui_controller.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Bounded background ThreadPoolExecutor defaults to three workers; voice submits without waiting. Simulated test covers three active plus fourth queued; live talk-while-working acceptance remains pending. |
| TSK-3 / AC-TSK-3 | P0 | Cancel, pause, resume | partial | [task_engine.py](../task_engine.py), [task_runtime.py](../task_runtime.py), [task_center.py](../task_center.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Named/latest cancellation and checkpoint pause/resume exist. Reviewed deterministic non-secret pending plans can reconstruct after restart; expired/secret slots require fresh paste/review. Arbitrary interrupted writes are not replayed; in-flight calls may finish. |
| TSK-4 / AC-TSK-4 | P0 | Crash and restart recovery | acceptance-pending | [task_store.py](../task_store.py), [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Startup marks active tasks interrupted and preserves pending deterministic non-secret approval plans for explicit reconstruction/resume. Regression covers reopened plan execution without write replay; actual process-kill/restart voice acceptance and expired secret context remain pending. |
| TSK-5 / AC-TSK-5 | P0 | Completion notification | partial | [task_engine.py](../task_engine.py), [main.py](../main.py) | Completion events queue tray toast/short speech until recording/speech/input/approval is idle. Two-second timing and overlapping-conversation acceptance are unmeasured; queued notices can be deferred. |
| TSK-6 / AC-TSK-6 | P0 | Step verification | implemented-with-evidence | [task_store.py](../task_store.py), [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Action completion now requires every tool result ok and verified:true or explicit step_verified retrieval evidence, plus at least one actual verified result. Failed/unverified UI steps cannot be hidden by unrelated success. Reviewed plan cursor stops at the first unverified step without replay; backend verifier quality still needs physical acceptance. |
| TSK-7 / AC-TSK-7 | P1 | Retries with backoff | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| TSK-8 / AC-TSK-8 | P1 | Task dependencies | acceptance-pending | [task_engine.py](../task_engine.py), [provider_interfaces.py](../provider_interfaces.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Planner dependencies refer to earlier tasks; engine waits without occupying a worker and blocks failed dependencies. Simulated ordered-dependency test exists; real Claude-to-Codex flow is unaccepted. |
| TSK-9 / AC-TSK-9 | P1 | Scheduled and recurring tasks | partial | [task_store.py](../task_store.py), [task_engine.py](../task_engine.py), [capability_tools.py](../capability_tools.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | SQLite schedules support explicit ISO timezone, recurrence intervals >=60 seconds and weekday filtering. Scheduler runs while Bilal runs; reboot timing/missed-execution reliability and requested weekday-9am flow need acceptance. |
| TSK-10 / AC-TSK-10 | P2 | Triggers | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### CTL

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| CTL-1 / AC-CTL-1 | P0 | App launch, focus, close, switch | partial | [desktop_worker.py](../desktop_worker.py), [agent_tools.py](../agent_tools.py), [test_desktop_worker.py](../tests/test_desktop_worker.py) | Discovered app IDs launch; observed windows support verified focus/close/switch-via-focus. Fuzzy discovery and twenty-app physical coverage are incomplete. |
| CTL-2 / AC-CTL-2 | P0 | Window management | acceptance-pending | [desktop_worker.py](../desktop_worker.py), [agent_tools.py](../agent_tools.py) | Observed-window focus/minimize/maximize/restore/left-right snap/close use Windows readback. Arbitrary move geometry and real multi-app state acceptance are incomplete. |
| CTL-3 / AC-CTL-3 | P0 | Clipboard read and write | implemented-with-evidence | [desktop_worker.py](../desktop_worker.py), [agent_tools.py](../agent_tools.py) | Native Windows clipboard roundtrip verified exactly 100000 bytes; original clipboard restored afterward. Read/write backend includes readback and secret-read guard. This acceptance covers text, not file/image clipboard formats. |
| CTL-4 / AC-CTL-4 | P0 | Keyboard input | partial | [desktop_worker.py](../desktop_worker.py), [agent_tools.py](../agent_tools.py), [test_desktop_worker.py](../tests/test_desktop_worker.py) | Text entry focuses the intended observed window, checks foreground identity, sets literal text and verifies value/focus. General shortcuts and real never-wrong-window acceptance remain incomplete. |
| CTL-5 / AC-CTL-5 | P0 | Browser control | partial | [dom_worker.py](../dom_worker.py), [dom_bridge.py](../dom_bridge.py), [agent_tools.py](../agent_tools.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Owned Chrome Playwright worker now opens/lists tabs, reads DOM, fills observed fields and clicks restricted observed elements with stale-ID checks and exact-host allowlisting. Five public sites were natively opened/read successfully; five-site form/control acceptance and personal-profile workflows remain unaccepted. |
| CTL-6 / AC-CTL-6 | P0 | Media control | partial | [spotify_worker.py](../spotify_worker.py), [media_controls.py](../media_controls.py), [agent_tools.py](../agent_tools.py), [test_spotify.py](../tests/test_spotify.py) | Spotify search/play plus WinRT play/pause/next/previous readback and Core Audio volume readback are implemented. Queue support and real playback/volume effect acceptance remain pending. |
| CTL-7 / AC-CTL-7 | P0 | File operations inside allowed folders | acceptance-pending | [file_tools.py](../file_tools.py), [capability_tools.py](../capability_tools.py), [tool_policy.py](../tool_policy.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Allowed-folder file read/search/create/copy/move/recycle/restore tools have backend path checks, limits, snapshots and hash/readback verification. Contract tests cover traversal/existing destinations/exact bytes/undo; real Recycle Bin and Windows edge-path acceptance are pending. |
| CTL-8 / AC-CTL-8 | P1 | Accessibility tree control | acceptance-pending | [desktop_worker.py](../desktop_worker.py), [test_desktop_worker.py](../tests/test_desktop_worker.py) | Observed-ID UI Automation read/invoke/text tools exist; real 10-app compatibility acceptance remains pending. |
| CTL-9 / AC-CTL-9 | P1 | Screenshot and vision check | partial | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py), [test_screen_dom.py](../tests/test_screen_dom.py) | User-selected memory-only capture can be described by Gemini without action tools. Goal-verifier integration, representative screen accuracy and physical capture acceptance remain pending. |
| CTL-10 / AC-CTL-10 | P1 | System actions | partial | [power_tools.py](../power_tools.py), [media_controls.py](../media_controls.py), [test_power_tools.py](../tests/test_power_tools.py) | Approval-bound sleep/shutdown/restart plus verified Core Audio volume API exist. Brightness/DND/lock and physical system-effect acceptance remain incomplete. |
| CTL-11 / AC-CTL-11 | P2 | Coordinate clicking by vision | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| CTL-12 / AC-CTL-12 | P2 | Multi monitor and virtual desktop awareness | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| CTL-13 / AC-CTL-13 | P2 | Shell command execution | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### AGT

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| AGT-1 / AC-AGT-1 | P0 | Run Claude Code non-interactively | acceptance-pending | [delegation.py](../delegation.py), [provider_keys.py](../provider_keys.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Official Claude Code 2.1.309 was installed under ignored local data and its version/flags checked. Bare/restricted no-tools JSON adapter exists; live execution is blocked by missing Anthropic API key. Subscription login alone is not used for this mode. |
| AGT-2 / AC-AGT-2 | P0 | Run Codex non-interactively | implemented-with-evidence | [delegation.py](../delegation.py), [task_runtime.py](../task_runtime.py) | Real authenticated read-only Codex adapter run returned a final answer and usage. This establishes prompt-in/final-answer-out for the current local CLI; project-only read isolation, writable execution and repeated handoff acceptance remain outside this evidence. |
| AGT-3 / AC-AGT-3 | P0 | Result capture and storage | partial | [delegation.py](../delegation.py), [task_runtime.py](../task_runtime.py), [task_store.py](../task_store.py), [task_center.py](../task_center.py) | A real Codex adapter answer/usage was captured; runtime stores redacted final text as task-linked artifacts with session metadata. Full raw event streams are not retained; complete durable delegated-result UX acceptance remains pending. |
| AGT-4 / AC-AGT-4 | P0 | Relay between agents | partial | [capability_tools.py](../capability_tools.py), [task_runtime.py](../task_runtime.py), [delegation.py](../delegation.py) | Stored artifacts can be passed verbatim as untrusted input into the next adapter. Codex single-run success does not establish Claude-to-Codex relay; live two-agent handoffs remain blocked by missing Claude key. |
| AGT-5 / AC-AGT-5 | P0 | Approval gate before write access | partial | [delegation.py](../delegation.py), [tool_policy.py](../tool_policy.py) | Delegation exposes read-only analysis only; no writable-agent mode exists. This blocks unapproved writes but does not implement the approved plan-to-write execution flow. |
| AGT-6 / AC-AGT-6 | P0 | Working directory and context pack | partial | [delegation.py](../delegation.py), [task_store.py](../task_store.py) | Adapter uses a temporary context directory and explicitly selected artifact, not a selectable project/context-file pack. Read-only CLI sandbox is not OS read/confidentiality isolation; allowed-project-only visibility is not established. |
| AGT-7 / AC-AGT-7 | P1 | Session resume | partial | [task_runtime.py](../task_runtime.py), [task_store.py](../task_store.py), [delegation.py](../delegation.py) | Provider session ID is persisted, but no external CLI session-resume path is implemented across restarts. |
| AGT-8 / AC-AGT-8 | P1 | Parallel agents | partial | [task_engine.py](../task_engine.py), [delegation.py](../delegation.py), [task_runtime.py](../task_runtime.py) | Independent subprocesses/context packs can run under engine limits. Codex single-run was accepted; actual parallel provider sessions/no-crosstalk evidence remains pending and Claude awaits API credentials. |
| AGT-9 / AC-AGT-9 | P1 | Usage and cost tracking | partial | [delegation.py](../delegation.py), [task_store.py](../task_store.py) | Real Codex usage capture is verified; Claude result parser supports token/cost metadata but is not live-tested. Remaining allowance, daily cost report and enforced provider budgets remain missing. |
| AGT-10 / AC-AGT-10 | P1 | Output parsing into tasks | partial | [provider_interfaces.py](../provider_interfaces.py), [task_engine.py](../task_engine.py), [task_center.py](../task_center.py) | Planner emits child tasks/dependencies visible in Task Center; external-agent plan-to-reorderable-checklist parsing is missing. |
| AGT-11 / AC-AGT-11 | P2 | GUI fallback for chat apps without an API | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| AGT-12 / AC-AGT-12 | P2 | Review loop | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| AGT-13 / AC-AGT-13 | P2 | MCP client support | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### MEM

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| MEM-1 / AC-MEM-1 | P0 | Preferences store | partial | [memory.py](../memory.py), [task_store.py](../task_store.py), [task_center.py](../task_center.py) | SQLite preferences plus settings/folder/hotkey state survive restart; full default-app/music/voice/approval-setting management is incomplete. |
| MEM-2 / AC-MEM-2 | P0 | Project profiles | acceptance-pending | [capability_tools.py](../capability_tools.py), [task_store.py](../task_store.py), [task_runtime.py](../task_runtime.py) | Reviewed project save/list/select tools persist folder/repo/documents/preferred-agent/notes and validate named paths against allowed folders. Selected profile is passed to planner as facts; real named-project context selection and delegated-file-context acceptance remain pending. |
| MEM-3 / AC-MEM-3 | P1 | Long term memory | partial | [memory.py](../memory.py), [agent_core.py](../agent_core.py), [test_business_learning.py](../tests/test_business_learning.py) | Confirmed facts persist and are used in reasoning; complete user-facing list/edit/delete management is missing. |
| MEM-4 / AC-MEM-4 | P1 | Writing style profile | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| MEM-5 / AC-MEM-5 | P1 | Contact book | partial | [task_store.py](../task_store.py), [capability_tools.py](../capability_tools.py) | Local contact storage, exact email validation and find/save tools exist; ambiguous-name one-question resolution and contact-management UX require acceptance. |
| MEM-6 / AC-MEM-6 | P1 | Local document search | partial | [file_tools.py](../file_tools.py), [task_store.py](../task_store.py), [capability_tools.py](../capability_tools.py) | Allowed-folder search reads md/txt/pdf/docx with bounds; artifact FTS exists. Chosen document folders are searched on demand rather than a persistent document index; representative correctness acceptance is pending. |
| MEM-7 / AC-MEM-7 | P2 | Session summaries | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| MEM-8 / AC-MEM-8 | P3 | Cross device sync | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### INT

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| INT-1 / AC-INT-1 | P1 | Gmail | partial | [business_tools.py](../business_tools.py), [setup_connections.py](../setup_connections.py), [test_business_learning.py](../tests/test_business_learning.py) | Plain-text draft/readback and human-approved exact-content send are implemented; broad read/search/summarize and live account acceptance are missing. |
| INT-2 / AC-INT-2 | P1 | Notion | partial | [business_tools.py](../business_tools.py), [test_business_learning.py](../tests/test_business_learning.py) | Shared-page search/read and child-note create/readback exist; general update/tasks/properties and live account acceptance are missing. |
| INT-3 / AC-INT-3 | P1 | Calendar | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| INT-4 / AC-INT-4 | P1 | Outreach pipeline | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| INT-5 / AC-INT-5 | P2 | WhatsApp drafting | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| INT-6 / AC-INT-6 | P2 | Content assistant | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| INT-7 / AC-INT-7 | P2 | Google Drive and Sheets | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| INT-8 / AC-INT-8 | P2 | Messaging apps (Slack, Discord) | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| INT-9 / AC-INT-9 | P2 | Social posting | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| INT-10 / AC-INT-10 | P3 | Payments, invoicing | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### EXT

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| EXT-1 / AC-EXT-1 | P1 | Skills folder | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| EXT-2 / AC-EXT-2 | P2 | Employee personas | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| EXT-3 / AC-EXT-3 | P2 | Skill sharing format | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| EXT-4 / AC-EXT-4 | P3 | Marketplace | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### QIN

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| QIN-1 / AC-QIN-1 | P0 | Double click the avatar to open the panel | acceptance-pending | [main.py](../main.py), [quick_input.py](../quick_input.py) | Avatar double-click opens focused Quick Input; dialog Escape behavior is inherited. Real under-0.5-second opening/focus trials remain pending. |
| QIN-2 / AC-QIN-2 | P0 | Literal payload | acceptance-pending | [literal_slots.py](../literal_slots.py), [quick_input.py](../quick_input.py), [agent_tools.py](../agent_tools.py), [file_tools.py](../file_tools.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | LiteralVault retains exact strings and resolves slots locally; contracts cover twenty diverse nonempty strings and UTF-8 file roundtrip. Full twenty-string target-app delivery gate remains pending. |
| QIN-3 / AC-QIN-3 | P0 | Speak while the panel is open | acceptance-pending | [quick_input.py](../quick_input.py), [ui_controller.py](../ui_controller.py), [task_runtime.py](../task_runtime.py) | Quick Input can stay open while talk shortcut records; controller clones local vault into queued tasks. Real voice-reference-to-right-slot acceptance is pending. |
| QIN-4 / AC-QIN-4 | P0 | Placeholder substitution | acceptance-pending | [literal_slots.py](../literal_slots.py), [task_runtime.py](../task_runtime.py), [agent_tools.py](../agent_tools.py), [provider_interfaces.py](../provider_interfaces.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Planner receives descriptors/tokens; local executor resolves arguments and masks returned values. Contracts cover slot cloning/resolution; full prompt-trace plus target-app end-to-end proof remains pending. |
| QIN-5 / AC-QIN-5 | P0 | Secret handling | partial | [literal_slots.py](../literal_slots.py), [quick_input.py](../quick_input.py), [agent_tools.py](../agent_tools.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Known token/card heuristics and explicit secret slots keep values out of descriptors/history; slots are memory-only and external secret connectors are blocked. Heuristic detection is not exhaustive; full log/prompt/memory scan and explicit cloud-egress approval workflow remain incomplete. |
| QIN-6 / AC-QIN-6 | P0 | Typed only commands | acceptance-pending | [quick_input.py](../quick_input.py), [ui_controller.py](../ui_controller.py), [task_runtime.py](../task_runtime.py) | Quick Input typed instructions submit to the same durable runtime as transcribed speech with cloned literal slots. Matched spoken/typed target-effect acceptance is pending. |
| QIN-7 / AC-QIN-7 | P1 | Several labeled snippets | acceptance-pending | [quick_input.py](../quick_input.py), [literal_slots.py](../literal_slots.py) | Multiple labeled snippets get independent opaque tokens and descriptors. Live ordinal references such as second link require semantic acceptance. |
| QIN-8 / AC-QIN-8 | P1 | Attachments | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| QIN-9 / AC-QIN-9 | P1 | Literal verification on approval | partial | [task_center.py](../task_center.py), [literal_slots.py](../literal_slots.py) | Policy approval view uses monospace and resolves exact local payloads, hiding secrets unless locally revealed. Confusable/look-alike character highlighting is missing. |
| QIN-10 / AC-QIN-10 | P1 | Panel history | partial | [quick_input.py](../quick_input.py), [task_store.py](../task_store.py) | Non-secret snippets are saved; panel clear clears active slots, but history recall and one-click persisted-history removal are not implemented. |
| QIN-11 / AC-QIN-11 | P2 | Dictation into the panel with exactness marking | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| QIN-12 / AC-QIN-12 | P2 | Spell mode for voice only entry | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### HOT

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| HOT-1 / AC-HOT-1 | P0 | Configurable global summon hotkey | acceptance-pending | [hold_to_talk.py](../hold_to_talk.py), [main.py](../main.py), [task_center.py](../task_center.py) | Hook-based configured chord defaults to left Ctrl+Shift+Space; Settings changes persist and apply after restart. Registration/remap behavior needs physical acceptance. |
| HOT-2 / AC-HOT-2 | P0 | Summon behavior | acceptance-pending | [hold_to_talk.py](../hold_to_talk.py), [main.py](../main.py), [ui_controller.py](../ui_controller.py) | Hook edges drive visible/listening state and hold release or toggle edges stop capture; Escape and silence paths exist. Each physical exit path remains unaccepted. |
| HOT-3 / AC-HOT-3 | P0 | Hold to talk and press to toggle | acceptance-pending | [hold_to_talk.py](../hold_to_talk.py), [task_center.py](../task_center.py), [main.py](../main.py) | Hold/toggle modes are selectable in Settings with restart to apply; 50 trials per mode at >=98% activation are pending. |
| HOT-4 / AC-HOT-4 | P0 | Instant feedback | acceptance-pending | [hold_to_talk.py](../hold_to_talk.py), [main.py](../main.py) | Shortcut signals cause local visual feedback before model/network work. Actual perceived/recorded latency remains unmeasured. |
| HOT-5 / AC-HOT-5 | P0 | Works over full screen apps and documented limits with elevated (admin) windows | planned | — | Full-screen/elevated-window trial evidence and documented verified limits are not available in baseline. |
| HOT-6 / AC-HOT-6 | P1 | Separate bindings | partial | [task_center.py](../task_center.py), [main.py](../main.py), [hold_to_talk.py](../hold_to_talk.py) | Talk binding can be remapped; stop-all has fixed Ctrl+Alt+Backspace and overlap guard. Separate remappable quick-input/pointer/stop bindings are incomplete; pointer mode absent. |
| HOT-7 / AC-HOT-7 | P1 | Conflict detection | partial | [hold_to_talk.py](../hold_to_talk.py), [task_center.py](../task_center.py) | Parser rejects some known Windows chords and settings reject talk/stop-all overlap. System input-language and other-app shortcut conflict detection/warnings remain incomplete. |
| HOT-8 / AC-HOT-8 | P2 | Gestures while summoned | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### SCR

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| SCR-1 / AC-SCR-1 | P1 | On demand screen capture | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py), [main.py](../main.py) | Explicit capture picker and Gemini vision answer path are implemented; images stay memory-only and no capture was physically performed during this work. Ten representative screen-description accuracy trials remain pending. |
| SCR-2 / AC-SCR-2 | P1 | Capture scope | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [main.py](../main.py) | Picker offers chosen window, chosen monitor, all monitors, pointer crop and dragged region. Physical scope accuracy, mixed-DPI and exclusive-fullscreen coverage are pending. |
| SCR-3 / AC-SCR-3 | P1 | Visible capture indicator | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Capture waits for a shown indicator, audits scope/indicator state and denies idle/cancelled capture. Real 100%-indicator-on-capture observation remains pending. |
| SCR-4 / AC-SCR-4 | P1 | Frames not stored by default | partial | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py) | PNG bytes stay in memory, frame is popped from task context for inference, and only answer text is persisted. No physical disk-absence scan or opt-in per-task image-saving feature exists yet. |
| SCR-5 / AC-SCR-5 | P1 | Sensitive window guard | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [task_center.py](../task_center.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Editable sensitive-window title/process terms block overlapping capture rectangles; simulated overlap test covers Bitwarden. Real password-manager/private-browser/banking capture and metadata edge cases remain pending. |
| SCR-6 / AC-SCR-6 | P1 | Hybrid grounding | partial | [screen_awareness.py](../screen_awareness.py) | Capture gathers available UIA name/role grounding and logs uia+vision or vision before a vision request. Local OCR and UIA-only answer fast paths are absent; this does not yet implement the full UIA-first/OCR-second/vision-last cascade. |
| SCR-7 / AC-SCR-7 | P1 | Pointer mode toggle | partial | [screen_awareness.py](../screen_awareness.py), [main.py](../main.py) | Visible overlay pointer can be entered from capture picker/tray, follows mouse and exits on Escape. It intercepts clicks for safety; configurable direct pointer binding and full toggle/always-visible physical acceptance remain incomplete. |
| SCR-8 / AC-SCR-8 | P1 | Click to ask | partial | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py), [main.py](../main.py) | Pointer click records position, resolves window/UIA target and crops to a memory-only question; answer is spoken through normal task notices. Local click-position answer bubble, UIA value grounding and >=90% accuracy over 20 elements are incomplete. |
| SCR-9 / AC-SCR-9 | P1 | Safe click | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Overlay consumes press/release, paints a nonzero-alpha hit surface and never forwards a click. Simulated Qt test leaves an underlying button untouched; real-app/elevated/exclusive-fullscreen safety remains pending. |
| SCR-10 / AC-SCR-10 | P1 | Region select | acceptance-pending | [screen_awareness.py](../screen_awareness.py) | Overlay supports drag-to-region with global coordinates; physical region-selection accuracy over multiple apps/mixed DPI remains pending. |
| SCR-11 / AC-SCR-11 | P1 | Point then command | partial | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py) | Point/crop supplies context to read-only screen questions. Persistent pointed-target action grounding for fix/copy/act and approval-bound point-to-action integration are not complete. |
| SCR-12 / AC-SCR-12 | P2 | Multi point | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SCR-13 / AC-SCR-13 | P2 | Live screen share | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SCR-14 / AC-SCR-14 | P2 | Guided pointing | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SCR-15 / AC-SCR-15 | P2 | Click for me | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SCR-16 / AC-SCR-16 | P2 | Local OCR as the first resort | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SCR-17 / AC-SCR-17 | P3 | Screen recording into tutorials or summaries | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### SAF

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| SAF-1 / AC-SAF-1 | P0 | Policy engine | partial | [tool_policy.py](../tool_policy.py), [agent_tools.py](../agent_tools.py), [ui_controller.py](../ui_controller.py), [screen_awareness.py](../screen_awareness.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Production tools use logged PolicyGate; trusted email/memory/power human decisions now also emit policy audit records. Screen capture logs explicit human-origin policy evidence. Universal metadata enforcement and removal of unguarded legacy paths remain incomplete. |
| SAF-2 / AC-SAF-2 | P0 | Approval card | partial | [capability_tools.py](../capability_tools.py), [task_runtime.py](../task_runtime.py), [tool_policy.py](../tool_policy.py), [task_center.py](../task_center.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | One review can approve up to 20 deterministic file/contact/project/schedule calls. Task Center supports edit/review-again, supersedes old consent and executes exact steps with cursor/no replay. Dynamic UI batches and external-agent write plans are excluded; universal whole-plan UX remains incomplete. |
| SAF-3 / AC-SAF-3 | P0 | Kill switch | partial | [main.py](../main.py), [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [delegation.py](../delegation.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Global stop-all cancels tasks, closes owned DOM session and revokes pending policy/business approvals; regression asserts revocation. Child-process cleanup exists, but under-two-second physical all-process stopping and in-flight provider cancellation remain unaccepted. |
| SAF-4 / AC-SAF-4 | P0 | Audit log | partial | [task_store.py](../task_store.py), [tool_policy.py](../tool_policy.py), [task_center.py](../task_center.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Hash-chained append-only SQLite audit, task/step/result state and a Task Center Audit view exist; trusted business decisions are recorded. Full command/plan/effect reconstruction acceptance remains pending; local hash chaining is not external tamper-proof storage. |
| SAF-5 / AC-SAF-5 | P0 | Allow lists | partial | [tool_policy.py](../tool_policy.py), [file_tools.py](../file_tools.py), [dom_worker.py](../dom_worker.py), [task_center.py](../task_center.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Settings expose allowed folders and exact-host browser domains; DOM request routes and public-network checks enforce browser destinations. Configurable app/recipient allowlists and full boundary acceptance remain incomplete. |
| SAF-6 / AC-SAF-6 | P0 | Prompt injection defense | partial | [tool_policy.py](../tool_policy.py), [agent_tools.py](../agent_tools.py), [agent_core.py](../agent_core.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Untrusted observations taint task context and require L2 before later mutations; simulated policy test exists. Full hostile-page/agent-output end-to-end injection suite and provenance coverage remain incomplete. |
| SAF-7 / AC-SAF-7 | P0 | Secrets handling | partial | [provider_keys.py](../provider_keys.py), [secret_store.py](../secret_store.py), [literal_slots.py](../literal_slots.py), [task_store.py](../task_store.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Actual Gemini/Groq project keys were migrated and readback-verified in Windows Credential Manager. Account DPAPI, heuristic redaction and local secret slots remain active; legacy env fallback/exhaustive runtime secret scans and arbitrary-secret detection remain gaps. |
| SAF-8 / AC-SAF-8 | P1 | Undo | partial | [file_tools.py](../file_tools.py), [capability_tools.py](../capability_tools.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | File writes take encrypted Windows snapshots, restore verifies hashes and file delete uses Recycle Bin. No draft-delete undo or delegated-edit snapshot workflow; real Windows restoration/recycle acceptance is pending. |
| SAF-9 / AC-SAF-9 | P1 | Data egress visibility | partial | [data-and-security.md](../docs/data-and-security.md), [configuration.md](../docs/configuration.md) | Documentation explains current egress; the specified in-app provider/data settings page is missing. |
| SAF-10 / AC-SAF-10 | P1 | Rate limits | partial | [screen_awareness.py](../screen_awareness.py), [task_store.py](../task_store.py) | Screen questions have a persisted 20-per-day count cap. General sends/agent-runs/hourly spend budgets and daily cost report remain unimplemented. |
| SAF-11 / AC-SAF-11 | P1 | Dry run mode | partial | [tool_policy.py](../tool_policy.py), [task_center.py](../task_center.py), [task_runtime.py](../task_runtime.py), [test_capability_foundation.py](../tests/test_capability_foundation.py) | Persisted dry-run setting makes PolicyGate return planned calls without execution/approval and has a contract test. Planner/provider requests still occur; full plan preview and all-effects end-to-end dry-run acceptance remain incomplete. |
| SAF-12 / AC-SAF-12 | P2 | Local only mode | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SAF-13 / AC-SAF-13 | P2 | Sensitive window guard | partial | [screen_awareness.py](../screen_awareness.py), [desktop_worker.py](../desktop_worker.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Editable screen-title/process blocklist rejects captures overlapping sensitive windows; generic UIA guards password/auth controls. Screen matching is heuristic and real banking/private-window/secure-desktop acceptance remains pending. |
| SAF-14 / AC-SAF-14 | P0 | Screen features are user triggered | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py), [test_screen_dom.py](../tests/test_screen_dom.py) | Capture requires an active user-selected session and visible indicator; idle/cancelled-session tests assert no ImageGrab calls. No physical idle-capture audit has yet been run. |
| SAF-15 / AC-SAF-15 | P1 | Screen content is untrusted data | acceptance-pending | [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py) | Screen-answer model receives explicit untrusted-data rules and no action tools. This separates screen description from execution; adversarial screen/provider acceptance remains pending. |
| SAF-16 / AC-SAF-16 | P2 | Redaction before sending | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### REL

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| REL-1 / AC-REL-1 | P0 | Benchmark suite | partial | [testing.md](../docs/testing.md), [test_capability_foundation.py](../tests/test_capability_foundation.py), [test_screen_dom.py](../tests/test_screen_dom.py) | 195 automated regressions passed in 22.078 seconds on native Windows, including screen/DOM and plan restart/revocation contracts. This is not the required 50-command injected end-state benchmark or per-build product pass-rate report. |
| REL-2 / AC-REL-2 | P0 | Structured logging and traces | partial | [task_store.py](../task_store.py), [task_runtime.py](../task_runtime.py), [agent_tools.py](../agent_tools.py), [task_center.py](../task_center.py) | Durable tasks, steps, artifacts, persistent turns and audit now link execution to task IDs with Task Center views. Full utterance/audio-to-result trace, tool-result audit completeness and searchable audit UX remain incomplete. |
| REL-3 / AC-REL-3 | P0 | Graceful degradation | partial | [task_engine.py](../task_engine.py), [task_runtime.py](../task_runtime.py), [ui_controller.py](../ui_controller.py), [provider_interfaces.py](../provider_interfaces.py) | Background failures are recorded and surfaced without blocking voice; queued/interrupted tasks persist and text input remains available. Provider outage queuing/recovery acceptance is pending. |
| REL-4 / AC-REL-4 | P0 | Silent startup and tray control | acceptance-pending | [startup_windows.py](../startup_windows.py), [launch_bilal.pyw](../launch_bilal.pyw), [main.py](../main.py), [test_background_startup.py](../tests/test_background_startup.py) | Hidden pythonw launcher, current-user startup shortcut, single-instance lock and tray exist; actual sign-in acceptance remains pending. |
| REL-5 / AC-REL-5 | P1 | Resource budget | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| REL-6 / AC-REL-6 | P1 | Health check screen | partial | [check_mvp_readiness.py](../check_mvp_readiness.py), [testing.md](../docs/testing.md) | Local readiness CLI reports configuration/format availability; comprehensive provider/network/account/permission UI health screen is missing. |
| REL-7 / AC-REL-7 | P1 | Auto update with rollback | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| REL-8 / AC-REL-8 | P2 | Opt in diagnostics | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

### SHP

| ID / case | Tier | Capability | Status | Evidence | Current assessment / remaining work |
| --- | --- | --- | --- | --- | --- |
| SHP-1 / AC-SHP-1 | P1 | Installer | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| SHP-2 / AC-SHP-2 | P1 | First run onboarding under 10 minutes | partial | [getting-started.md](../docs/getting-started.md) | Manual setup guidance exists; guided fresh-machine onboarding under ten minutes is unverified. |
| SHP-3 / AC-SHP-3 | P1 | Licensing review | planned | — | Not implemented in the reviewed baseline; requires code, tests and applicable acceptance evidence. |
| SHP-4 / AC-SHP-4 | P1 | Clear privacy notice | implemented-with-evidence | [README.md](../README.md), [data-and-security.md](../docs/data-and-security.md) | Plain-language data destinations and storage/approval boundaries are documented; review remains necessary whenever network behavior changes. |
| SHP-5 / AC-SHP-5 | P2 | Pricing and billing | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |
| SHP-6 / AC-SHP-6 | P2 | Bring your own keys versus hosted | planned | — | No implementation evidence assessed against this full capability yet. P2/P3 remain explicit future scope. |

## Release gates that cannot be replaced with mocks

Automated contract tests are necessary, but physical, provider and account gates require the real environment. No fabricated timing, successful send, screenshot accuracy score or elapsed dogfooding period may be used to close these gates.

| Gate | Pass condition | Evidence required | Status |
| --- | --- | --- | --- |
| GATE-BENCHMARK | At least 90% pass on 50 scripted commands with expected end states. | automated-text-injection-and-end-state-verification | Pending |
| GATE-HOTKEY | At least 98% activation in 50 trials; test hold and toggle modes separately with 50 trials each. | physical-windows-hotkey-trials | Pending |
| GATE-STT | At least 90% correct across 50 independently scripted spoken commands. | physical-microphone-and-selected-STT-provider | Pending |
| GATE-WAKE | Fewer than one false activation per hour of normal use and at least 90% true activation on fresh independent recordings. | one-hour-background-audio-plus-independent-positive-trials | Pending |
| GATE-DOGFOOD | Owner uses Bilal daily for seven days and completes 20 consecutive successful Flow A handoffs. | seven-real-days-and-authorized-agent-runs | Pending |
| GATE-SAFETY | Zero unapproved L2 actions; all injection tests blocked, with reconstructable audit evidence. | automated-adversarial-contracts-and-live-audit-review | Pending |
| GATE-SETUP | Fresh Windows machine to first successful command in under ten minutes. | fresh-install-observation | Pending |
| GATE-EXACT | 20 literal strings arrive byte for byte; zero secrets in logs, prompt traces and memory. | automated-and-target-app-roundtrip-with-secret-scan | Pending |
| GATE-SCREEN | At least 90% correct on 20 pointed elements, pointer clicks never reach underlying app; accurate descriptions for ten test screens. | physical-pointer-capture-plus-vision-provider-validation | Pending |
| GATE-APPS | 20 apps launch/focus correctly; accessibility read/click works in ten common apps. | installed-app-compatibility-matrix | Pending |
| GATE-ACCOUNTS | Authorized Gmail, Notion and calendar workflows reach and verify requested external state. | explicit-account-setup-and-live-user-authorized-tests | Pending |
| GATE-HONESTY | README documents known failures and matches recorded capability/acceptance status. | documentation-review | Pending |

Account setup/live acceptance stays pending until authorized and configured. Provider-authenticated Claude/Codex execution also requires installed clients, valid sessions and independently verified isolation/permissions. A read-only CLI flag alone is not proof that the child can see only the permitted project.

## Standard flows and situations

Flows A–E and situations S1–S16 are separately tracked in `capabilities.json`. **None is accepted end to end at this baseline.** Individual component success does not close a full flow: Flow A includes verified artifact relay, approved scoped writes, snapshots and completion evidence; Flow D includes placeholder-only model context and local exact substitution; Flow E includes click interception and sensitive-window capture guards.

## How to update this record

1. Reference capability IDs in the implementation and regression tests.
2. Record the actual source/test paths and the precise scope they establish.
3. Update implementation status without converting pending physical/provider acceptance into a pass.
4. For each accepted case, attach date, environment, observed result and a redacted report/artifact reference. Keep recordings, credentials and private account data out of this repository.
5. Recompute JSON counts and keep this Markdown matrix aligned with it.
6. Update README known limitations and release gates when behavior changes.

The JSON preserves the original tier, description and acceptance text for every capability. Its release-gate and flow records supplement the specification; they do not lower its acceptance thresholds.
