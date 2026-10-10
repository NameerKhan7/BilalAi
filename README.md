# BilalAI

A Python voice assistant for Windows, under active development.

Current features:
- Push-to-talk command recorder with automatic silence stopping, local WAV saving and playback.
- Explicit Groq transcription with an editable transcript and locally saved text.
- Gemini answers with short replies, bounded follow-up context and a Clear chat control.
- An experimental local `hey Bilal` wake-word detector and microphone test.
- Local voice-calibration tools, with a separate personalized candidate profile.
- CPU training and regression-check utilities.

Wake-word recognition is still experimental. Push-to-talk recording is available as the reliable manual activation path. Notion, Spotify and Chrome launch commands are connected. Spoken replies and tray controls are not connected yet.

## Current one-button flow

Close the old window and run main.py. Click Record once, wait for Speak now, and say a question or command. Recording automatically continues into transcription and request handling. Separate Transcribe and Ask buttons are no longer part of the voice workflow. Send typed text remains as an optional fallback.

Supported local app commands:
- Hey Bilal, open Notion.
- Hey Bilal, open Spotify.
- Open Chrome.

App commands use local executable paths or Windows Start-app IDs, without calling Gemini. On this machine Notion and Spotify are Windows Store apps; both were launched and their running processes verified during development. Information questions alone go to Gemini. Unknown app names receive an unsupported-command message rather than being silently changed to another app.

Basic browser commands also work: Open YouTube; Search YouTube for Pakistani food; Search for weather in Karachi on Google; Open YouTube and search for Pakistani food in Chrome. These open search URLs in installed Chrome; they do not read pages or click results.

Voice recording now automatically uploads the selected clip to Groq for transcription because it is part of the requested one-button workflow. Local commands are then executed locally. Questions send text and recent chat to Gemini. WAV, transcript and response files remain excluded from Git. Escape cancels recording or a pending request; closing the app also stops pending processing stages.

## Spotify search and playback

Spotify playback requests now run through a separate local Windows UI Automation worker. Close the old Bilal window and restart main.py after installing requirements.txt. Try "Open Spotify and play jazz" or "Play Blinding Lights by The Weeknd on Spotify". Spotify must be installed and signed in; Bilal never handles login prompts.

The worker opens Spotify's search URI, verifies the search field, invokes a visible song row's Play control, and checks Spotify's Windows media session against the selected title. It reports success only after that verification. A playlist or album result, advertisements, non-English controls, or Spotify versions that do not expose accessible result controls can cause a clear unverified-playback error. Live playback was verified on the installed Spotify version: the executor searched for Blinding Lights, invoked its song-row Play button, and Windows reported Blinding Lights by The Weeknd actively playing. Search verification handles Spotify's ComboBox control and encoded spaces. Song selection is scoped to the Search results grid.

For a direct diagnostic test:

```powershell
.\venv\Scripts\python.exe .\spotify_worker.py --query "Blinding Lights"
```

A diagnostic report is saved locally in logs/spotify_latest.json, excluded from Git. It contains the failed stage or verified result, not screenshots or credentials. Escape stops pending automation; audio already playing may continue. No Spotify API key or Premium assumption is used; playback remains subject to your account's normal restrictions.

## Run the baseline

Use Python 3.11 and install the project dependencies in a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\wakeword.py --seconds 60
```

Say `hey Bilal`, then try normal conversation and similar phrases. The baseline uses a 0.80 threshold, two consecutive matching frames, and a 0.6-second repeat cooldown. The terminal displays microphone and processing latency.

The configuration file `config/config.yaml` currently contains JSON-compatible YAML. The shared audio feature models and synthetic baseline classifier are included under `models/`.

## Test command recording

```powershell
.\venv\Scripts\python.exe .\main.py
```

Or double-click `test_command_recording.bat`. In the recorder window:

1. Click Record command or press Space.
2. Wait for Speak now.
3. Say: Open YouTube and search for Pakistani food.
4. Stop speaking and wait for automatic stopping after one second of silence.
5. Click Play recording and verify that the entire sentence is clear, including its first and last words.

Space again or Escape stops recording manually. Nothing spoken is executed yet. The recorder waits up to six seconds for speech and limits a command to fifteen seconds. Recordings stay local in the ignored `recordings/` folder. It briefly measures room noise before showing Speak now, so wait for that prompt before talking.

Repeat with three different sentences. If Windows blocks the microphone, enable microphone access for desktop apps in Windows Settings. After recording passes, test speech-to-text below.

Automated recording-boundary and encoding checks:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Test speech-to-text

Close any old recorder window and relaunch `main.py`. Record a command, then click Transcribe. That button uploads only the selected recording to Groq for transcription. Recording, playback and voice-calibration tools remain local. Nothing is sent automatically after recording.

Set `GROQ_API_KEY` in your local `.env` file; `.env.example` shows the required variable without including a secret. The app uses Groq's multilingual `whisper-large-v3-turbo` transcription endpoint with automatic language detection and a short app-name vocabulary hint, including Chrome and Spotify. The hint guides spelling; transcript text is not altered with blanket word replacements. See [Groq speech-to-text documentation](https://console.groq.com/docs/speech-to-text).

The transcript appears in the window and is saved beside its WAV under the ignored `recordings/` folder. Missing keys, rejected credentials, connection errors, timeouts and usage limits produce a retryable message. No spoken command is executed yet.

Test three different commands in your usual voice and confirm that the complete meaning is preserved. The service connection was verified with generated speech; no private microphone clip was uploaded during development tests. After your voice passes transcription, the next milestone is testing Gemini answers below.

## Test Gemini answers

The local GEMINI_API_KEY was verified with model listing and text generation. The installed google-genai SDK uses gemini-3.5-flash-lite, listed with free-tier access subject to project quota. The code does not reject keys by prefix or enable paid billing. Sources: https://ai.google.dev/gemini-api/docs/api-key and https://ai.google.dev/gemini-api/docs/pricing.

Close the old window and relaunch main.py. Record, Transcribe, review or edit the text, then click Ask Bilal. You can also type a question directly. Ask Bilal sends text and up to six recent question/answer pairs to Gemini, without sending the WAV to Gemini. Transcribe separately sends the WAV to Groq.

Try a question, then a follow-up: Remember that my test code word is mango; What code word did I mention? Replies appear in the right pane. Clear chat or closing the app resets session context. Replies associated with a recording are saved locally as .answer.txt beside its WAV. Desktop actions, live web lookup and spoken replies are not connected yet.

GEMINI_MODEL optionally overrides the tested model. Missing keys, quota errors, unavailable models and connection failures produce safe retryable messages. Local text-to-speech is the next milestone after this test.

## Voice calibration

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py --other-samples 3
```

Follow the prompts. Short recordings and their analysis stay on the local computer under `training/recordings/`, which is excluded from Git. No audio is uploaded. See `training/VOICE_CALIBRATION.md`.

Personalized model weights, private calibration reports, downloaded training assets, generated audio and `.env` API keys are excluded from this repository. A personalized profile can be used locally when its model and settings are present; it needs fresh real-voice validation before being made the default.

## Training and limitations

The baseline is an experimental personal-use model. Its synthetic tests do not establish reliable always-on performance. Use the documented microphone checks before depending on it. The roadmap and training notes are in `BilalAI_6Week_Roadmap.md` and `training/`.

The code uses openWakeWord audio feature extractors, Piper-generated samples and public background embeddings. Some training datasets carry noncommercial terms. Source links and asset licensing notes are in `training/README.md`; review those before commercial redistribution or deployment.
