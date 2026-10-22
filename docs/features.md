# Feature reference

[Documentation](README.md) · [Project overview](../README.md) · [User guide](user-guide.md) · [Field acceptance](FIELD_ACCEPTANCE.md)

Bilal AI is a Windows LLM agent with local tools. Gemini chooses available tools; Python and Windows execute them. Tool results feed back into the agent so it can choose another step and check the result.

**Status: experimental.** Implementation is not proof of a successful live test. Gmail and Notion live account acceptance remains pending. Physical voice, background playback, and Windows sign-in checks also need validation on the target PC.

## Capability map

| Area | Implemented behavior | Main boundary |
| --- | --- | --- |
| Activation | Local acoustic detector and offline full-phrase verification | No speaker identity or acoustic echo cancellation |
| Recording | Silence-ended wake/manual capture or global left Ctrl + left Shift hold/release | Ordinary limit 90s; new hold/clarification captures bounded 600s |
| Conversation | Gemini answers and selects tools; explicit activation for each new voice turn by default | Automatic follow-up capture is disabled |
| Desktop | Discover apps/windows, inspect and operate accessible controls | Coverage depends on Windows accessibility support |
| Music | Search Spotify, attempt playback, verify actual media status | Spotify must be installed and usable |
| Web | Open Chrome searches/URLs; separately read public page text | No general DOM or screenshot-based browser agent |
| Missing details | Ask general questions aloud; receive hold-to-talk clarification; show email paste dialog | Original task retained in process; no sending approval implied |
| Memory | Save approved preferences, aliases, and pronunciation corrections | No automatic model retraining or extra permissions |
| Gmail | Create/read back a plain-text draft; review before sending | Separate account setup; no attachments; live tests pending |
| Notion | Search/read shared pages; create/read back a requested note | Only integration-accessible pages; live tests pending |
| Power | Propose sleep/shutdown/restart; execute after confirmation | Windows may refuse or delay the operation |
| Background operation | Hidden tray app; optional sign-in startup | Requires a signed-in Windows session |

## 1. Activation and false-trigger prevention

The supported trigger is **“Hey Bilal”**, not “hey” alone. Automatic activation follows these gates:

1. A local ONNX classifier identifies a possible wake phrase using the live `candidate_threshold` of 0.30 and two-frame confirmation. The standalone diagnostic retains `threshold` 0.80.
2. An offline speech verifier checks the complete phrase before the companion appears.
3. Audio arriving during verification stays buffered for command capture.
4. Groq transcribes the activated recording. The automatic command must still contain the trigger; otherwise the controller discards it before agent execution.

Candidate verification sends no audio to Gemini or Groq. The verifier uses a local `base.en` model installed by `setup_wake_verifier.py`. It supplies a “Hey Bilal.” vocabulary prompt and applies strict phrase/confidence checks; that context alone is insufficient for acceptance.

If verification cannot load or fails, automatic activation is disabled. Manual recording and typing remain available. **Listen for Hey Bilal** toggles automatic activation.

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

A new hold capture starts through global **left Ctrl + left Shift**. Keeping the keys held suppresses silence/no-speech endpoints; release sends the captured utterance. New hold and clarification captures have a 600-second chunk bound. Hitting the bound processes the chunk and does not hide the UI while held. Ordinary wake/manual capture retains the defaults above. The shortcut polls only left modifier states and does not log or intercept typing.

Releasing hold-to-talk hides the companion immediately and ends the active session, while the task and audio reply may continue in the background. There is no automatic recording after the reply in the default build. Existing internal 15s follow-up support is dormant unless explicitly enabled in code. Captured commands and spoken clarifications go to Groq. Audio, transcript, and answer files are saved under ignored `recordings/`. Typed requests bypass capture and transcription. Recognition can mishear names, mixed languages, quiet speech, and song titles; contextual interpretation does not guarantee the intended meaning.

**Code:** [audio_capture.py](../audio_capture.py), [ui_controller.py](../ui_controller.py). **Tests:** [capture](../tests/test_audio_capture.py).

## 3. Reasoning and tool execution

Assistant commentary and clarification use English. The active prompt encourages concise relevant follow-up questions and light situational humor without jokes during sensitive approvals/errors. This is model guidance, not a guarantee of perfect language or judgment.

The flow is **understand → observe → act → observe again → reply or ask**. A question can receive a direct answer; an action request can invoke several tools and inspect their results.

The model receives a defined catalogue. It cannot invent an executable tool, approve its own actions, or run arbitrary model-written shell commands. Arguments are validated locally. Desktop control IDs come from observations and must be refreshed when actions change the interface.

The reasoning loop allows up to 12 rounds with a 180-second reasoning budget. This is not a hard end-to-end deadline for every network call or app operation. Failed tools, unavailable controls, provider errors, or an exhausted budget can stop a task.

“I will open Spotify” is not proof of playback. Success must come from actual tool results. The UI uses a verified completion state only when the trace contains successful verification and no failed tool result.

**Code:** [agent_core.py](../agent_core.py), [agent_tools.py](../agent_tools.py), [request_router.py](../request_router.py), [ui_controller.py](../ui_controller.py).

## 4. Desktop apps and accessible controls

Bilal discovers registered Windows apps rather than requiring a fixed list of every name. Launching uses an app ID returned by discovery. An installed program missing from that registration source may not appear.

After launch, Bilal can list windows, inspect accessible controls, activate observed buttons/links/menus, and enter literal text in editable fields. A separate desktop worker owns Windows accessibility handles.

Discovery does not establish control over every app. Canvas-only interfaces, inaccessible elements, changed layouts, and unusual dialogs can block progress. General desktop control does not interpret screenshots or use arbitrary visual coordinates.

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

Cancellation prevents later steps and can stop capture/speech; it cannot undo completed work. During processing, an offline Windows English recognizer listens for a small cancellation grammar. Noise/accent can affect it. Tray cancellation is the fallback. Escape applies when Bilal has focus, not globally.

Optional startup installs a current-user sign-in shortcut through `pythonw.exe`; a lock prevents duplicate GUI instances. It is not a pre-login service. Keep the installed project/virtual environment paths or update the shortcut after moving them.

**Code:** [main.py](../main.py), [voice_cancel.py](../voice_cancel.py), [startup_windows.py](../startup_windows.py), [launch_bilal.pyw](../launch_bilal.pyw).

## 13. Data and verification boundaries

Wake verification stays local. Command recordings go to Groq. Requests, relevant observations, recent conversation, and confirmed preferences can go to Gemini. Connected operations use Gmail/Notion APIs. Local recordings, transcripts, answers, traces, state, and credentials are excluded from Git; exclusion is not encryption. Account tokens use Windows-user-bound encryption.

Desktop failures can require fresh observation. Uncertain account writes require service inspection before retrying. Missing configuration is a connection requirement. Wake verification failures disable automatic activation rather than handing background speech to the agent.

The **23 October 2026** regression run passed 154 automated tests; [testing](testing.md) records the scope and separate wake replay evidence. Simulated account/power effects and synthetic audio do not prove live delivery, physical recognition, or sign-in startup. Follow [field acceptance](FIELD_ACCEPTANCE.md) for those checks.
