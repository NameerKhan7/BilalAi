# BilalAI

A Python voice assistant for Windows, under active development.

Current features:
- Push-to-talk command recorder with automatic silence stopping, local WAV saving and playback.
- Explicit Groq transcription with a transcript display and locally saved text.
- An experimental local `hey Bilal` wake-word detector and microphone test.
- Local voice-calibration tools, with a separate personalized candidate profile.
- CPU training and regression-check utilities.

Wake-word recognition is still experimental. Push-to-talk recording is available as the reliable manual activation path. Model answers, spoken replies, desktop actions and tray controls are not connected yet.

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

Set `GROQ_API_KEY` in your local `.env` file; `.env.example` shows the required variable without including a secret. The app uses Groq's multilingual `whisper-large-v3-turbo` transcription endpoint with automatic language detection. See [Groq speech-to-text documentation](https://console.groq.com/docs/speech-to-text).

The transcript appears in the window and is saved beside its WAV under the ignored `recordings/` folder. Missing keys, rejected credentials, connection errors, timeouts and usage limits produce a retryable message. No spoken command is executed yet.

Test three different commands in your usual voice and confirm that the complete meaning is preserved. The service connection was verified with generated speech; no private microphone clip was uploaded during development tests. After your voice passes transcription, the next milestone is connecting model answers.

## Voice calibration

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py --other-samples 3
```

Follow the prompts. Short recordings and their analysis stay on the local computer under `training/recordings/`, which is excluded from Git. No audio is uploaded. See `training/VOICE_CALIBRATION.md`.

Personalized model weights, private calibration reports, downloaded training assets, generated audio and `.env` API keys are excluded from this repository. A personalized profile can be used locally when its model and settings are present; it needs fresh real-voice validation before being made the default.

## Training and limitations

The baseline is an experimental personal-use model. Its synthetic tests do not establish reliable always-on performance. Use the documented microphone checks before depending on it. The roadmap and training notes are in `BilalAI_6Week_Roadmap.md` and `training/`.

The code uses openWakeWord audio feature extractors, Piper-generated samples and public background embeddings. Some training datasets carry noncommercial terms. Source links and asset licensing notes are in `training/README.md`; review those before commercial redistribution or deployment.
