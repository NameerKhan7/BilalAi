# Personalized wake-word candidate

The original real calibration session detected 2/5 hey Bilal recordings and rejected all five hee-haa recordings at the baseline policy. There was no threshold that separated every real positive from every real negative.

A separate candidate was fine-tuned using those local recordings, retaining the baseline neural-network weights and scaling. It also uses synthetic examples, background features and complete streaming windows from 120 negative training clips. Raw microphone recordings and personal training features remain in the ignored local recordings folder.

Recording-level cross-validation excluded each original positive/negative pair and all its augmentations together. At the candidate threshold 0.30 with two-frame confirmation, all five positive holdouts passed and all five negative holdouts were rejected. Ten synthetic wake clips passed and ten other synthetic phrase clips were rejected. Threshold selection used calibration results, so these are diagnostic checks; a fresh independent real recording session is required before replacing the baseline. Continuous background reliability is not established.

The candidate is stored in `models/personalized/hey_bilal.onnx`; its settings and fold scores are in `models/personalized/calibration.json`. Baseline model weights and threshold remain unchanged.

Run a fresh guided check:

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py --model personalized --other-samples 3
```

Follow the prompts for five hey Bilal recordings, five hee-haa recordings, and one each of hey Bill, hey Bella and hello Bilal. Speak naturally once after each SPEAK NOW cue. All recordings stay local. The report identifies the actual model hash and includes false detections by negative label. The tool does not automatically change the default model.

For a live candidate test:

```powershell
.\venv\Scripts\python.exe .\wakeword.py --model personalized --seconds 60
```

The regular command without --model still uses the baseline as a fallback.
