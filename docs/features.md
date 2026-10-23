# Feature reference

[Documentation](README.md) · [Project overview](../README.md) · [User guide](user-guide.md) · [Field acceptance](FIELD_ACCEPTANCE.md)

Bilal AI is a Windows LLM agent with local tools. Gemini chooses available tools; Python and Windows execute them. Tool results feed back into the agent so it can choose another step and check the result.

**Status: capability foundation, not full-spec completion.** Read the [138-capability target](CAPABILITY_SPEC.md) and [current assessment/known blockers](CAPABILITY_STATUS.md). Implementation is not proof of a successful live test. Gmail and Notion live account acceptance remains pending. Physical voice, background playback, and Windows sign-in checks also need validation on the target PC.

## Capability map

| Area | Implemented behavior | Main boundary |
| --- | --- | --- |
| Activation | Global left Ctrl + left Shift hold/release; gated optional wake | Wake defaults off without fresh independent acceptance |
| Tasks | Three workers, dependencies, persisted steps/results/history, in-app schedules | Physical/live acceptance and full-goal verification remain incomplete |
| Exact input | Quick Input with locally resolved literal slots | Secret slots expire; heuristic detection is incomplete |
| Files | Allowed-folder reading/search and reviewed file effects with versions | No arbitrary filesystem access or shell executor |
| Screen questions | Explicit picker/indicator and answer-only vision | 20/day; pointer/secure-desktop edge cases unaccepted |
| Delegation | Restricted read-only Codex/Claude CLI adapters | Codex local live passed; Claude key/live test pending; no write mode |
| Recording | Silence-ended wake/manual capture or global left Ctrl + left Shift hold/release | Ordinary limit 90s; new hold/clarification captures bounded 600s |
| Conversation | Gemini answers and selects tools; explicit activation for each new voice turn by default | Automatic follow-up capture is disabled |
| Desktop | Discover apps/windows, inspect and operate accessible controls | Coverage depends on Windows accessibility support |
| Music | Search Spotify, attempt playback, verify actual media status | Spotify must be installed and usable |
| Web | Quiet research, explicit legacy Chrome opening, owned-profile DOM tools | Owned browser requires exact domain Settings and does not attach personal tabs |
| Missing details | Ask general questions aloud; receive hold-to-talk clarification; show email paste dialog | Original task retained in process; no sending approval implied |
| Memory | Save approved preferences, aliases, and pronunciation corrections | No automatic model retraining or extra permissions |
| Gmail | Create/read back a plain-text draft; review before sending | Separate account setup; no attachments; live tests pending |
| Notion | Search/read shared pages; create/read back a requested note | Only integration-accessible pages; live tests pending |
| Power | Propose sleep/shutdown/restart; execute after confirmation | Windows may refuse or delay the operation |
| Background operation | Hidden tray app; optional sign-in startup | Requires a signed-in Windows session |

## 1. Activation and false-trigger prevention

Default production activation is **left Ctrl + left Shift** held while speaking. The Settings dialog can change the chord or use toggle mode; restart to apply. Left Ctrl + left Shift alone is opt-in. The global keyboard hook tracks configured keys, forwards typing to other apps, and ignores injected keystrokes. It does not record typed text.

Wake defaults off unless `data/wake_acceptance.json` records independent evidence no older than 30 days: at least 50 positive trials with at least 90% true activation, at least 3,600 negative seconds, and fewer than one false activation per hour. Installing/training a model does not unlock it. An absent/stale/failed report keeps it disabled.

When accepted and enabled, the trigger is **“Hey Bilal”**, not “hey” alone. Automatic activation follows these gates:

1. A local ONNX classifier identifies a possible wake phrase using the live `candidate_threshold` of 0.30 and two-frame confirmation. The standalone diagnostic retains `threshold` 0.80.
2. An offline speech verifier checks the complete phrase before the companion appears.
3. Audio arriving during verification stays buffered for command capture.
4. Groq transcribes the activated recording. The automatic command must still contain the trigger; otherwise the controller discards it before agent execution.

Candidate verification sends no audio to Gemini or Groq. The verifier uses a local `base.en` model installed by `setup_wake_verifier.py`. It supplies a “Hey Bilal.” vocabulary prompt and applies strict phrase/confidence checks; that context alone is insufficient for acceptance.

If verification cannot load or fails, automatic activation is disabled. Manual recording and typing remain available. **Listen for Hey Bilal (acceptance required)** cannot bypass the independent acceptance gate.

This is not speaker recognition. Media or another person saying the full trigger can still activate Bilal. It does not remove speaker audio from the microphone. Fresh background-playback tests remain necessary.

**Code:** [wake_service.py](../wake_service.py), [wake_verifier.py](../wake_verifier.py), [wakeword_gate.py](../wakeword_gate.py), [ui_controller.py](../ui_controller.py). **Tests:** [activation](../tests/test_wake_activation.py), [acceptance](../tests/test_wake_acceptance.py).

## 2. Recording and transcription

Capture runs locally until detected silence, manual finish, cancellation, or a limit. Current `CaptureConfig` defaults:

| Setting | Default | Meaning |
| --- | --- | --- |
| Pause allowance | 4 seconds | Silence after speech can finish capture |
| Initial wait | 10 seconds | Stop if no speech is detected within the capture window |
| Maximum capture | 90 seconds | Longer dictation is cut off |
| Format | 16 kHz, mono, 16-bit | Audio supplied to transcription |
| Processing block | 20 ms | Endpoint calculation interval |
| Manual calibration | 0.30 seconds | Estimate background noise |
| Pre-roll / tail | 0.25 seconds each | Keep short context around speech |

Wake capture reuses the microphone stream and buffered audio without restarting calibration. The initial wait is not ten additional seconds after the popup appears. Timings are code defaults, not exposed user settings.

A new hold capture starts through global **left Ctrl + left Shift**. Keeping the keys held suppresses silence/no-speech endpoints; release sends the captured utterance. New hold and clarification captures have a 600-second chunk bound. Hitting the bound processes the chunk and does not hide the UI while held. Ordinary wake/manual capture retains the defaults above. The global hook tracks the configured chord, forwards keystrokes, and does not record typed text.

Releasing hold-to-talk hides the companion immediately and ends the active session, while the task and audio reply may continue in the background. There is no automatic recording after the reply in the default build. Existing internal 15s follow-up support is dormant unless explicitly enabled in code. Captured commands and spoken clarifications go to Groq. Command audio and transcripts are saved under ignored `recordings/`. Production background answers are task artifacts in the local database; the legacy synchronous path also writes `.answer.txt` files. Typed requests bypass capture and transcription. Recognition can mishear names, mixed languages, quiet speech, and song titles; contextual interpretation does not guarantee the intended meaning.

**Code:** [audio_capture.py](../audio_capture.py), [ui_controller.py](../ui_controller.py). **Tests:** [capture](../tests/test_audio_capture.py).

## 3. Reasoning and tool execution

Assistant commentary and clarification use English. The active prompt encourages concise relevant follow-up questions and light situational humor without jokes during sensitive approvals/errors. This is model guidance, not a guarantee of perfect language or judgment.

The flow is **understand → observe → act → observe again → reply or ask**. A question can receive a direct answer; an action request can invoke several tools and inspect their results.

The model receives a defined catalogue. It cannot invent an executable tool, approve its own actions, or run arbitrary model-written shell commands. Arguments are validated locally. Desktop control IDs come from observations and must be refreshed when actions change the interface.

The reasoning loop allows up to 12 rounds with a 180-second reasoning budget. This is not a hard end-to-end deadline for every network call or app operation. Failed tools, unavailable controls, provider errors, or an exhausted budget can stop a task.

“I will open Spotify” is not proof of playback. Success must come from actual tool results. The durable runtime requires successful verified results for action traces before marking completion. This conservative check can still miss a multi-part goal not represented by the trace; the full-goal acceptance criterion remains open.

**Code:** [agent_core.py](../agent_core.py), [agent_tools.py](../agent_tools.py), [request_router.py](../request_router.py), [ui_controller.py](../ui_controller.py).

## 4. Desktop apps and accessible controls

Bilal discovers registered Windows apps rather than requiring a fixed list of every name. Launching uses an app ID returned by discovery. An installed program missing from that registration source may not appear.

After launch, Bilal can list windows, inspect accessible controls, activate observed buttons/links/menus, and enter literal text in editable fields. A separate desktop worker owns Windows accessibility handles.

Discovery does not establish control over every app. Canvas-only interfaces, inaccessible elements, changed layouts, and unusual dialogs can block progress. General desktop action tools do not use vision coordinates. A separate explicit screen-question path can analyze a selected image but has no action tools.

Generic controls block sending, publishing, deletion, purchases, authentication/security changes, and power actions. These are tool boundaries, not instructions to seek another route around them.

**Code:** [agent_tools.py](../agent_tools.py), [desktop_worker.py](../desktop_worker.py).

## 5. Spotify playback

For “Play Blinding Lights by The Weeknd on Spotify,” the model can pass song and artist to the Spotify adapter. It can interpret a likely transcription error such as “Blind Lights” from context; this remains a judgment, not a guarantee.

The adapter searches, attempts playback, and checks Windows media-session information for the actual track. Opening Spotify or search results alone is insufficient for a playback success claim. Missing sessions, unexpected tracks, account restrictions, connectivity, or app changes can prevent completion.

**Code:** [spotify_tools.py](../spotify_tools.py), [agent_tools.py](../agent_tools.py).

## 6. Browser search and public reading

Factual research uses quiet `web_search` (Bing RSS, up to five results) and `read_webpage`. Search can be blocked; snippets are leads, not verified facts. `prayer_times` independently resolves a confirmed city/country through Nominatim/OpenStreetMap, then uses Aladhan’s coordinate endpoint for the ISO date with method 1 (Karachi) by default. Returned coordinates, date, method ID, timezone, and Fajr data are checked; returned times are calculated starts, not mosque congregation times. No automatic GPS/IP city lookup exists.

`ResearchGuard` permits at most two searches, three page reads, two browser openings, and two prayer lookups per agent run, and rejects identical normalized repeats. Blocked or very short error pages cannot serve as source evidence. Bilal can explicitly open Google, YouTube, or Wikipedia searches in Chrome and open HTTP(S) URLs when requested. Opening results does not prove research or a page task finished.

The public webpage reader returns bounded text, source URLs, and continuation support. It does not use browser login cookies, inspect screenshots, or read private/local-network resources. Signed-in content needs a connected service or supported desktop interaction. App/web content is untrusted observation, not authority to override the user's request or bypass approval.

**Code:** [browser_tools.py](../browser_tools.py), [web_reader.py](../web_reader.py), [agent_tools.py](../agent_tools.py).

## 7. Contextual input

When a detail is missing, `request_input` asks a short question. An `email` field opens the paste dialog; a `text` field is spoken with no dialog, and the user answers through hold-to-talk or a verified wake turn. The controller retains the pending task and wraps the transcribed answer as clarification context. The existing task stays in the current conversation.

Supported fields are one complete email address or non-secret text. Input must be nonempty and at most 2,000 characters; the email field rejects incomplete/multiple addresses. Invalid email input stays visible for correction. Enter/**Continue** submits the email dialog once, closes it, and resumes work. Spoken text answers use the held capture’s release and the same local validation. Cancel stops the pending continuation.

Pasting a recipient does **not** approve sending. The box is not for passwords, API keys, or payment details. Pending clarification lives in the process; do not rely on it surviving a restart.

**Code:** [contextual_input.py](../contextual_input.py), [ui_controller.py](../ui_controller.py).

## 8. Confirmed memory and wake improvement

Two separate mechanisms support improvement:

- **Confirmed memory:** the agent proposes a preference, alias, or pronunciation correction. Human review precedes local SQLite storage. Confirmed information can inform reasoning/transcription. Saved procedures are guidance, not permission to perform sensitive actions. Credentials are not suitable memories.
- **Reviewed wake examples:** users collect and label recordings locally. Evaluation and candidate training are separate developer steps. Nothing automatically replaces the deployed model.

Guided collection pauses wake monitoring and opens a console. Each session requests ten positives and ten negatives, playing each clip before label acceptance. Training preparation requires ten valid reviewed clips per class and two sessions containing both classes. Hash checks exclude changed/missing clips.

Candidates go separately under `models/candidates/`. Counts or completed training do not establish improved recognition; independent evaluation must precede deliberate promotion. Bilal does not continuously train on every “hey.” “Hey” alone should remain a negative example.

**Code:** [memory.py](../memory.py), [business_tools.py](../business_tools.py), [wake_learning.py](../wake_learning.py), [collect_wake_examples.py](../collect_wake_examples.py), [train_reviewed_wake.py](../train_reviewed_wake.py). **Procedure:** [calibration](../training/VOICE_CALIBRATION.md).

## 9. Gmail draft and send review

Gmail needs Bilal's own Desktop OAuth connection. A Codex connection does not connect this standalone app.

The agent creates an unsent plain-text draft with a complete recipient, subject, and body. Bilal reads it back and presents actual recipient/content for review. Sending is available only through the dedicated human approval UI, not an agent send tool or generic click.

Approval is bound to the reviewed draft and can be used once. A changed draft needs fresh review. Rejection prevents sending but need not delete the unsent draft. For an uncertain write/send, inspect Gmail before retrying to avoid duplicates. Attachments and general mailbox management are unavailable in the current tool catalogue.

**Live account acceptance remains pending.** **Code:** [business_tools.py](../business_tools.py), [memory.py](../memory.py), [setup_connections.py](../setup_connections.py), [main.py](../main.py).

## 10. Notion pages and notes

Notion needs a separate integration token and page sharing. Bilal searches accessible pages by title, reads content/nested blocks, and creates/reads back requested notes under a selected parent.

Signing into Notion elsewhere does not grant workspace-wide access. Share the intended parent with the integration. Requested note creation is a write and does not use Gmail's send approval. After an uncertain creation result, check the parent before repeating.

**Live account acceptance remains pending.** **Code:** [business_tools.py](../business_tools.py), [setup_connections.py](../setup_connections.py).

## 11. Sleep, shutdown, and restart

The agent proposes one of three fixed local power actions. Human review shows the exact action. Confirmation is one-shot, bound to the request, and expires after two minutes. Rejection/cancellation has no power effect. There is no arbitrary command field or remote target.

Shutdown/restart preserve Windows save-work handling without forcing applications closed. Sleep uses native Windows suspension. Permissions, unsaved apps, settings, and hardware can block/delay the result. Windows accepting a request is not proof the machine transition finished. An asleep/shut-down PC cannot hear Bilal's trigger.

**Code:** [power_tools.py](../power_tools.py), [business_tools.py](../business_tools.py). **Tests:** [power tools](../tests/test_power_tools.py), with actual machine effects mocked.

## 12. Companion, speech, cancellation, and startup

The transparent **96 × 120 pixel** character/orb appears near the bottom center and stays hidden before activation. After reply completion it hides. Hold release hides it immediately while processing/audio may continue. Automatic follow-up capture is disabled by default. Missing-input/approval dialogs keep necessary interaction visible. The full conversation opens on demand.

The eight artwork states are idle, listening, processing, speaking, success, error, loading, and inactive. Qt animates supplied 2D artwork with pose transitions, gestures, blinks, and speech motion; it is not a 3D renderer. Speech uses an installed Windows voice and system output. Engine availability does not prove audible sound.

Cancellation prevents later steps and can stop capture/speech; it cannot undo completed work. When enabled, the optional offline Windows English recognizer listens during processing for a small cancellation grammar. Default production wake is off, so do not rely on spoken interruption being available; use the global stop shortcut or tray. Noise/accent can affect it. Tray cancellation is the fallback. Escape applies when Bilal has focus, not globally. **Left Ctrl + left Alt + Backspace** globally stops pending tasks, speech/capture and screen interaction through the main stop path; completed effects remain.

Optional startup installs a current-user sign-in shortcut through `pythonw.exe`; a lock prevents duplicate GUI instances. It is not a pre-login service. Keep the installed project/virtual environment paths or update the shortcut after moving them.

**Code:** [main.py](../main.py), [voice_cancel.py](../voice_cancel.py), [startup_windows.py](../startup_windows.py), [launch_bilal.pyw](../launch_bilal.pyw).

## 13. Data and verification boundaries

Wake verification stays local. Command recordings go to Groq. Requests, relevant observations, recent conversation, and confirmed preferences can go to Gemini. Connected operations use Gmail/Notion APIs. Local recordings, transcripts, answers, traces, state, and credentials are excluded from Git; exclusion is not encryption. Account tokens use Windows-user-bound encryption.

Desktop failures can require fresh observation. Uncertain account writes require service inspection before retrying. Missing configuration is a connection requirement. Wake verification failures disable automatic activation rather than handing background speech to the agent.

The current regression and limited live evidence are recorded in [capability status](CAPABILITY_STATUS.md); [testing](testing.md) records the scope and separate wake replay evidence. Simulated account/power effects and synthetic audio do not prove live delivery, physical recognition, or sign-in startup. Follow [field acceptance](FIELD_ACCEPTANCE.md) for those checks.


## 14. Durable tasks, dependencies, and history

Production input enters `TaskRuntime` and a SQLite-backed `TaskEngine`. The structured planner can split a request into up to eight child intents with dependencies. There are three worker slots by default; dependent tasks wait without occupying a worker. Real multi-command semantic accuracy remains acceptance-pending.

States include queued, running, paused, waiting_approval, blocked, done, failed, cancelled, and interrupted. Task Center displays actual stored task state, steps and errors. History searches saved answers/drafts/agent output through SQLite FTS. Command context and task-linked artifacts persist across process restarts.

Persistence does not guarantee resumption of every task. Running/queued/paused work is recovered as interrupted, and writes are not blindly replayed. Memory-only frames and literal vaults cannot be recovered. Pause/cancel act at cooperative boundaries; in-flight calls can complete. Status queries read stored state rather than infer completion from a reply.

The scheduler persists timezone-aware commands and intervals and requires exact-step review before creation. It runs inside Bilal: the app must stay running and Windows must be awake. Full calendar/OS wake scheduling is not supplied. The current weekday filter uses the Pakistan timezone offset.

**Code:** [task_runtime.py](../task_runtime.py), [task_engine.py](../task_engine.py), [task_store.py](../task_store.py), [task_center.py](../task_center.py), [provider_interfaces.py](../provider_interfaces.py).

## 15. Exact pasted payloads and Quick Input

Double-clicking the avatar or choosing **Paste exact text / quick input** opens a focused panel. Add a label and pasted text, then type an instruction or use hold-to-talk while the panel remains open. Planning receives a token/descriptor; local resolution substitutes the original string into tool arguments without asking the model to rewrite it. Each task receives its own vault copy.

Literal input is bounded at 2 MB per string. Added non-secret snippets can persist locally. Secret-marked/detected snippets are memory-only and excluded from descriptors/history values. Closing/clearing the panel clears its vault, but already queued tasks retain their copies. Restart loses those memory-only copies; an expired slot fails rather than inventing text.

Known-token/card patterns provide heuristic secret detection, not exhaustive prevention. External delegation rejects detected secrets; approved cloud-secret transport is not a complete feature. Do not place credentials in the instruction itself. Provider keys use Settings. Exact preservation in the local vault is not proof of delivery to every target app; end-to-end target acceptance remains pending.

**Code:** [literal_slots.py](../literal_slots.py), [quick_input.py](../quick_input.py), [agent_tools.py](../agent_tools.py), [task_runtime.py](../task_runtime.py).

## 16. Policy, folders, versions, and exact-step approval

Tool policy checks risk level, folder scope, literal use and dry-run state before dispatch. Allowed folders start empty. Reads/searches require a selected root; private directories and credential files/content are blocked. Text/document reads are bounded at 2 MB and support UTF-8, PDF and DOCX extraction. Search is on demand, not a complete indexed corpus.

Writes, moves, recycling, restores, schedule/contact/project saves use review gates. A new copy is lower-risk and does not require the same review as a write. File writes preserve exact UTF-8 bytes, verify readback, and snapshot an overwritten file. Snapshots are Windows-user-encrypted and checked by hash. Recycling supports individual files, not directory deletion. Version history is not a universal rollback for external app/account actions.

Task Center **Approvals** shows the precise pending tool and arguments. Secret values are hidden unless explicitly revealed locally. Approval expires after ten minutes, is bound to exact arguments/task, and is consumed once. A level-three action additionally requires typing `CONFIRM`. Approving resumes only that step; earlier effects are not replayed and the remaining whole plan is not automatically executed. Legacy Gmail/memory/power cards remain separate, with power's two-minute expiry.

Dry run records planned calls without their effects. The append-only, hash-linked audit records policy/task events and can be verified locally; it is not a complete OS-wide effects ledger or a security boundary against machine compromise.

**Code:** [tool_policy.py](../tool_policy.py), [file_tools.py](../file_tools.py), [capability_tools.py](../capability_tools.py), [task_store.py](../task_store.py), [task_center.py](../task_center.py).

## 17. Owned Chrome DOM and media controls

The Playwright worker starts Chrome with a separate persistent profile at `data/browser-profile/`. It does not attach to personal Chrome tabs. **Settings → Set allowed browser domains** accepts exact hostnames, with no wildcards. Both navigation and resource routes are guarded; required third-party hosts can cause incomplete pages until deliberately allowed. Public/local-network validation still applies.

Tools list owned tabs, observe text/elements, fill an observed field and read it back, or click an observed control. Tab/element observations can expire. Password/file/submit fields and authentication, publishing, buying, deletion or other protected labels are blocked. A click alone is unverified until its effect is observed. This is limited DOM automation, not universal browser control.

Spotify play/pause/next/previous uses WinRT media sessions, checks the observed effect, and requires exactly one Spotify session. System volume uses the default Core Audio output with readback. These tools do not synthesize global media-key presses.

**Code:** [dom_bridge.py](../dom_bridge.py), [dom_worker.py](../dom_worker.py), [media_controls.py](../media_controls.py).

## 18. Explicit screen questions and pointer mode

A screen question opens a choice dialog for one window, one monitor, all monitors, or a pointed/dragged region. A visible sharing indicator appears before capture. Selected PNG frames stay in memory and go to Gemini; derived answers can persist as task artifacts. The screen answer path has no action tools.

A configurable title/process block list rejects overlapping sensitive windows. Accessibility password fields and apparent secrets are excluded from grounding. These are heuristics, not image redaction or a guarantee that no sensitive pixels remain. Inspect the chosen scope before sharing. Capture is bounded to 20 questions per local date and resized to a 1600 × 1200 maximum envelope.

Pointer mode intends to consume presses/releases rather than click the underlying app. This phase remains partial until secure-desktop, exclusive-fullscreen, and mixed-DPI physical checks pass. It does not authorize autonomous clicking based on vision. Cancel/stop-all closes the overlay/session. A frame lost on restart requires fresh explicit capture.

**Code:** [screen_awareness.py](../screen_awareness.py), [task_runtime.py](../task_runtime.py), [main.py](../main.py).

## 19. Read-only external-agent delegation

Codex/Claude adapters run bounded subprocesses in temporary context directories with action tools disabled. They receive the task and explicitly selected non-secret artifact, not an automatic whole-project context pack. Answers and available session/usage metadata become saved artifacts. No approved agent write mode, session resume, or full plan-to-write handoff exists.

A local read-only Codex live check passed. Official Claude Code CLI **2.1.309** is installed locally; its adapter needs a separately configured `ANTHROPIC_API_KEY` through Settings and has not passed live authenticated acceptance. Subscription login alone is not used for bare mode. Missing credentials fail before a Claude prompt is sent.

Read-only tool restrictions are not OS project-only confidentiality isolation. Do not claim the subprocess cannot read any other machine files. Saved session IDs are metadata, not implemented resume capability; usage metadata is not complete subscription allowance or pricing tracking.

**Code:** [delegation.py](../delegation.py), [provider_keys.py](../provider_keys.py), [task_runtime.py](../task_runtime.py).
