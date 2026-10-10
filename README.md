# BilalAI

A Windows desktop assistant with a model-driven observe-act-verify agent loop.

## How it works

Voice -> Groq transcription -> Gemini interprets the goal -> local tools -> observations back to Gemini -> another action or a verified outcome.

Every request goes through the agent. There is no regular-expression command router and no list of accepted sentences. Ordinary questions can be answered without executing tools. For tasks, the model chooses tools and receives their actual results before deciding what to do next.

The agent can:
- Discover registered installed apps and launch a returned app ID.
- Discover open windows and inspect their visible accessibility controls.
- Enter literal text into observed editable controls and invoke observed buttons, links and menu items.
- Search and play Spotify songs with Windows playback verification.
- Open Google, YouTube and Wikipedia searches in Chrome.
- Use recent conversation for follow-up requests.

An installed-app entry does not guarantee that its interface can be operated. Generic desktop interaction depends on Windows accessibility controls. Canvas-only interfaces, missing accessibility information and unsupported control patterns may block a task. Visual reasoning and browser DOM automation are not implemented. Authentication, security/privacy changes, destructive actions, purchases and sending/publishing are blocked in generic controls; they need dedicated confirmation-aware tools.

## Run

From the code directory, using Python 3.11:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\main.py
```

Close any old Bilal window first. Set GEMINI_API_KEY and GROQ_API_KEY in the local .env file. Use .env.example as the template; do not commit credentials.

Say Hey Bilal to activate the floating character and start listening, or click the companion. Speak after the listening expression appears. The local wake detector remains experimental and can be disabled in the popup. Recording, transcription and agent handling continue automatically. Send typed text is available for testing without recording. Escape stops pending steps; completed actions are not undone and playback already started may continue.

The interface shows the tool the agent is currently using. Tasks have a 12-round / 180-second reasoning budget, bounded tool timeouts and cancellation checks.

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
