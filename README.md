# BilalAI

A Python voice assistant for Windows, under active development.

Current features:
- An experimental local `hey Bilal` wake-word detector and microphone test.
- Local voice-calibration tools, with a separate personalized candidate profile.
- CPU training and regression-check utilities.

Wake-word recognition is still experimental. Push-to-talk command recording is the next MVP milestone. Transcription, model answers, spoken replies, desktop actions and tray controls are not connected yet.

## Run the baseline

Use Python 3.11 and install the project dependencies in a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\wakeword.py --seconds 60
```

Say `hey Bilal`, then try normal conversation and similar phrases. The baseline uses a 0.80 threshold, two consecutive matching frames, and a 0.6-second repeat cooldown. The terminal displays microphone and processing latency.

The configuration file `config/config.yaml` currently contains JSON-compatible YAML. The shared audio feature models and synthetic baseline classifier are included under `models/`.

## Voice calibration

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py --other-samples 3
```

Follow the prompts. Short recordings and their analysis stay on the local computer under `training/recordings/`, which is excluded from Git. No audio is uploaded. See `training/VOICE_CALIBRATION.md`.

Personalized model weights, private calibration reports, downloaded training assets, generated audio and `.env` API keys are excluded from this repository. A personalized profile can be used locally when its model and settings are present; it needs fresh real-voice validation before being made the default.

## Training and limitations

The baseline is an experimental personal-use model. Its synthetic tests do not establish reliable always-on performance. Use the documented microphone checks before depending on it. The roadmap and training notes are in `BilalAI_6Week_Roadmap.md` and `training/`.

The code uses openWakeWord audio feature extractors, Piper-generated samples and public background embeddings. Some training datasets carry noncommercial terms. Source links and asset licensing notes are in `training/README.md`; review those before commercial redistribution or deployment.
