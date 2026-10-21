# BilalAI

A Windows desktop assistant with a model-driven observe-act-verify agent loop.

## How it works

Voice -> Groq transcription -> Gemini interprets the goal -> local tools -> observations back to Gemini -> another action or a verified outcome.

Ordinary requests go through the agent; explicit cancellation controls are handled locally before execution. There is no regular-expression command router and no list of accepted sentences. Ordinary questions can be answered without executing tools. For tasks, the model chooses tools and receives their actual results before deciding what to do next.

The agent can:
- Discover registered installed apps and launch a returned app ID.
- Discover open windows and inspect their visible accessibility controls.
- Enter literal text into observed editable controls and invoke observed buttons, links and menu items.
- Search and play Spotify songs with Windows playback verification.
- Open Google, YouTube and Wikipedia searches in Chrome.
- Use recent conversation and user-confirmed persistent preferences for follow-up requests.
- Read public webpage text and source URLs with bounded continuation.
- Propose memory corrections for confirmation.
- Prepare Gmail drafts for recipient/content-bound human approval, and operate shared Notion pages once accounts are connected.

An installed-app entry does not guarantee that its interface can be operated. Generic desktop interaction depends on Windows accessibility controls. Canvas-only interfaces, missing accessibility information and unsupported control patterns may block a task. Visual reasoning and browser DOM automation are not implemented. Authentication, security/privacy changes, destructive actions, purchases and sending/publishing are blocked in generic controls; Gmail now has a dedicated draft-specific approval path; deletion, purchases and generic publishing remain unavailable.

## Run

From the code directory, using Python 3.11:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\main.py
```

Close any old Bilal window first. Set GEMINI_API_KEY and GROQ_API_KEY in the local .env file. Use .env.example as the template; do not commit credentials.

Say Hey Bilal to activate the floating character and start listening, or click the companion. Speak after the listening expression appears. The local wake detector remains experimental and can be disabled in the popup. Recording, transcription and agent handling continue automatically. Send typed text is available for testing without recording. Escape stops pending steps; completed actions are not undone and playback already started may continue.

The compact character shows listening/processing/speaking states; optional details and approvals are available through the tray. Tasks have a 12-round / 180-second reasoning budget, bounded tool timeouts and cancellation checks.

## Examples

- Play blind Lights on Spotify by The Weeknd.
- Find the Spotify window and tell me what is in its search field. Do not change anything.
- Open an installed app by its name.
- Search YouTube for Pakistani food.
- Explain the difference between a website and a web app.

These are examples, not sentence templates. The model interprets wording and context. For music it can resolve a plausible title from an imperfect transcript and artist; search results and actual playback are the source of truth.

## Verified behavior

The real Gemini agent interpreted "Play blind Lights on Spotify by The Weeknd", called spotify_play with "Blinding Lights The Weeknd", received verified playback and reported the actual song. The corrected Spotify adapter reads the search ComboBox, updates a retained previous query when necessary, and invokes the song-row Play button in the Search results grid.

Installed-app discovery returned 271 entries on the development PC, and actual Spotify control inspection returned visible controls. This establishes working discovery and observation, not universal compatibility with those apps.

Automated tests cover the model tool loop, recovery from failed tools, cancellation, mutation sequencing, schema validation, recording, transcription, media verification and safe failure reporting:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -q
```

## Source structure

- agent_core.py: model reasoning, bounded conversation, manual tool-call loop and task traces.
- agent_tools.py: declared tool schemas, validation and desktop-worker bridge.
- desktop_worker.py: persistent Windows accessibility session with observed window/control IDs.
- request_router.py: forwards every request to the agent; no phrase parsing.
- spotify_worker.py / spotify_tools.py: verified music playback capability.
- main.py: voice/typed interface and task-progress updates.
- audio_capture.py / stt_client.py: recording and transcription.

Each generic action invalidates the prior control IDs. The agent must observe again before another action. Generic activation never counts as a verified completed task.

## Data and task logs

Speech clips go to Groq for transcription. Text requests, recent conversation and relevant app observations go to Gemini for reasoning. Desktop actions run locally. There is no model-generated shell-command executor.

Recordings, transcripts, replies and per-task traces in logs/agent_*.json stay local and are excluded from Git. Traces contain tool arguments, observations, failures and final outcomes, so they may include private app content. logs/spotify_latest.json contains the latest playback diagnostic. API keys and personalized training recordings/models are also excluded.

## Experimental wake word

Push-to-talk is the reliable activation path. The local hey Bilal wake-word detector remains experimental:

```powershell
.\venv\Scripts\python.exe .\wakeword.py --seconds 60
.\venv\Scripts\python.exe .\calibrate_wakeword.py --other-samples 3
```

The baseline uses threshold 0.80 with two matching frames. Shared feature models and the synthetic baseline are included; personalized models and private calibration recordings remain local. See training/VOICE_CALIBRATION.md for calibration.

## Character interface and longer commands

The native PySide6 popup uses the supplied Bilal character/orb references, with eight expression states, crossfades, head gestures, blinking, speech articulation and microphone-driven glow. The default UI is a 96 by 120 pixel transparent companion at the bottom center of the active screen, above the taskbar. It shows only the person and orb. Click it to start or finish recording; drag it to reposition. Right-click or use the tray for settings and an optional separate conversation window. The tray can reopen it or quit the app. Windows SAPI reads replies when Speak replies is enabled; its installed voices determine pronunciation. The speaking pose follows real speech state. Success is shown only when the task trace contains verification without a failed tool.

Recording waits 4 seconds of silence after speech, gives 10 seconds to start, and permits up to 90 seconds per command. Internal pauses are kept in the saved audio. Click the companion again while listening to end a command sooner, or Cancel/Escape to discard pending processing. Pauses longer than 4 seconds still finish a command automatically; this is not semantic end-of-speech prediction.

The idle state uses the orb portrait; the other poses come from the supplied eight-expression reference. Real-time motion is animated in Qt, not a video or a 3D character rig. Colors and typography are configurable in brand_theme.json. Its current values follow the attached references; Notion brand guidelines are pending completion of the user's Notion connection.

Render all states without microphone or API usage:

```powershell
.\venv\Scripts\python.exe .\main.py --preview-all
```

Screenshots are saved in the ignored ui_preview/ directory. Character assets and their prompts are documented in assets/character/ASSET_NOTES.md.

The previous large card is hidden by default. Controls, typed requests and full replies are available only on demand through the tray menu. The character stays anchored while its head, eyes and mouth animate; vertical bobbing is disabled. Speech word events animate the mouth where supported, with a speaking-state fallback. This is a 2D animated sprite implementation, not a rigged 3D character.

## Request grounding and diagnostics

The current request takes precedence over completed tasks in conversation history. Ambiguous app targets should trigger clarification before an app is changed. Reports about a mistaken action are treated as reports, not new commands to execute their quoted text. Each reasoning run receives current Asia/Karachi date/time and tomorrow's calendar date; weather answers must establish the city and inspect the requested forecast day.

logs/agent_latest.json points to the latest real task trace, including start time, model, previous request, current request, tool steps and outcome. Unit and diagnostic model tests disable runtime trace writing so they do not become the latest user task. These private files remain excluded from Git.

The companion starts hidden while local wake-word monitoring stays active. A wake or manually initiated request reveals it. It stays visible through recording, execution and spoken output, then hides automatically after completion. Pending speech prevents early dismissal; a new request prevents an older dismissal timer from hiding an active task. The tray remains available while the avatar is hidden.

Ctrl+C in the launching terminal requests a clean GUI shutdown. The signal handler does not raise inside animation callbacks; a GUI timer stops animation, speech and pending processing. Painter scopes always release their drawing device, including on exceptions. Quit Bilal from the tray is also supported.

## Start automatically with Windows

Windows sign-in startup is installed for the current user through a Bilal AI.lnk shortcut in Windows' configured Startup folder. It points to this project's venv/Scripts/pythonw.exe and launch_bilal.pyw, so no console window opens. The avatar stays hidden while local Hey Bilal listening is active; spoken replies use the default Windows audio output. Single-instance locking prevents duplicate microphones/windows.

Microphone startup failures retry automatically with a bounded delay. JSON tool workers explicitly use the console Python interpreter with CREATE_NO_WINDOW, so background startup does not break their standard input/output. Diagnostics go to the ignored logs/background.log and logs/ui_startup.json files.

Install/update startup:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py
```

Disable automatic startup:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py --remove
```

Startup runs after this Windows user signs in, not before login. The project directory and virtual environment must remain at their installed paths. It does not require a Codex scheduled task or administrator-level Windows service. Quit Bilal from its tray menu to stop it for the current session.

## Six-area MVP work

See [the baseline](docs/MVP_BASELINE.md) and [implementation/acceptance status](docs/MVP_IMPLEMENTATION.md). The software paths are implemented and tested, but live account workflows and fresh physical wake acceptance are still pending. Do not describe the MVP as fully validated.

## Contextual input

When a task needs a missing detail, the agent calls request_input. A small temporary box asks for it, including a complete recipient address for email. Enter or Continue submits the detail and closes the box; Cancel or Escape abandons the pending task. The original dictated subject/body remain in conversation context. The box is absent during ordinary tasks, and wake recording pauses while it awaits input. Providing an address is not sending approval: Gmail still requires its separate review step. Credentials should be entered only through account setup, never this popup.

## Readiness and physical acceptance

Run `python check_mvp_readiness.py --tests` with the project virtual environment for local readiness checks. The private report is saved to logs/mvp_readiness.json. No account APIs or microphone recording are invoked. See [field acceptance](docs/FIELD_ACCEPTANCE.md) for physical wake/speaker/sign-in checks, reviewed wake collection and the pending Gmail/Notion acceptance sequence. Failures are spoken when Speak replies is enabled.

## Laptop power control

Say ?Hey Bilal, put my laptop to sleep?, ?shut down my laptop?, or ?restart my laptop?. The model proposes request_system_power, then stops for a dedicated confirmation showing the exact action. Clicking Sleep now, Shut down now, or Restart now executes locally; Reject, closing the dialog, or cancellation executes nothing. Confirmations expire after two minutes and cannot be replayed. Save work before confirming. Generic controls and power shortcuts cannot substitute for this approval path.

Shutdown/restart use a fixed local shutdown.exe argument list with /t 0 and no /f, preserving Windows' save-work handling. Sleep uses SetSuspendState with hibernation disabled and wake events retained. Windows permissions, hardware and application blockers can prevent an action; accepted requests do not count as verified shutdown/restart. While asleep, Bilal cannot hear Hey Bilal; wake the laptop through normal hardware controls first.

Power tests use simulated Windows effects; no live power transition was performed during development. References: [Windows shutdown command](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/shutdown), [Windows sleep API](https://learn.microsoft.com/en-us/windows/win32/api/powrprof/nf-powrprof-setsuspendstate).

## Wake activation and background video audio

Wake activation now requires two local checks: the wake detector produces a candidate, then an offline Whisper base.en model must recognize the complete “Hey Bilal” phrase. The companion stays hidden during verification. Audio captured while verification runs is retained in RAM so the first command words are not lost. A wake-started command without that phrase in its final transcript is silently discarded before agent execution. Manual tray/click/typed requests still work normally.

One-time setup after installing requirements:

```powershell
.\venv\Scripts\python.exe .\setup_wake_verifier.py
```

The public model is downloaded to the ignored models/wake_asr folder from a fixed SYSTRAN revision, with its published weight checksum verified. Wake verification runs locally with no provider calls. It uses wake-phrase vocabulary context plus a strict recognition-confidence gate; vocabulary context alone never activates it. Only after local phrase confirmation does normal command recording/transcription begin. Missing or failed verification disables automatic activation; it does not fall back to score-only activation. Restart Bilal after setup or updates.

This reduces false activation from ordinary video dialogue. It is not speaker recognition or playback echo cancellation: a video actually saying “Hey Bilal” can still trigger it. Real microphone testing with background playback remains necessary. [Local speech runtime](https://github.com/SYSTRAN/faster-whisper).
