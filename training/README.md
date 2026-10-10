# BilalAI wake-word baseline

This folder trains a custom `hey Bilal` classifier on the existing openWakeWord audio embeddings. It uses a CPU-compatible Piper ONNX multi-speaker model, rather than the Linux/GPU sample generator in the upstream automatic notebook.

## Reproduce

From the `code` directory in PowerShell:

```powershell
.\venv\Scripts\python.exe training\download_assets.py
.\venv\Scripts\python.exe training\train_cpu.py
.\venv\Scripts\python.exe training\verify_stream.py
```

Training dependencies: the existing requirements plus `onnx==1.17.0`.

The run generates 1,200 active utterances: one positive and one negative per speaker. Positive clips use explicit IPA phonemes for bi-LAAL, with two final-vowel variants; the voice model default pronunciation is excluded. Earlier default-pronunciation clips remain only in the ignored cache and are excluded from training. Speaker IDs 0–399 train, 400–479 validate, and 480–559 form the original development test, and 560–599 form a fresh final test. The first version was revised after its streaming test exposed false triggers; final streaming figures use the fresh voices. Training audio receives four noise/reverb/gain augmentations. 6,528 shifted hard-negative and silence examples are added for the second training revision. General negative embeddings are split into contiguous non-overlapping thirds. The classifier is a 64/32-unit MLP; its scaling and weights are exported together to ONNX. Threshold selection uses the validation partition only. Metrics and the model hash are written to `training_report.json`.

This is a small synthetic baseline. Accuracy on a Pakistani accent, the actual microphone and the intended room remains unmeasured. Negative window error rates are not equivalent to always-on false activations per hour. The model should be tested with real speech before wiring it into a permanent background assistant.

## Test locally

```powershell
.\venv\Scripts\python.exe wakeword.py --list-devices
.\venv\Scripts\python.exe wakeword.py --seconds 60
.\venv\Scripts\python.exe wakeword.py --wav your_recording.wav
```

You can also double-click `test_wakeword.bat` in the `code` folder. During the microphone test, say `hey Bilal` ten times at different distances. Then test normal conversation, `Bilal`, `hey Bill`, `hey Bella`, TV audio and typing. Record missed detections and false triggers. Adjust the threshold only using a calibration session; repeat with a separate test session. Microphone processing is local and does not save or upload audio.

## Sources and licenses

- Piper libritts_r medium voice: https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/libritts_r/medium. 904 US English speakers. The model card lists its source dataset as CC BY 4.0: https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/libritts_r/medium/MODEL_CARD.
- openWakeWord feature extractors v0.5.1: https://github.com/dscripka/openWakeWord/releases/tag/v0.5.1. Consult upstream licensing for these pretrained assets; the repository code is Apache 2.0.
- Background embeddings: https://huggingface.co/datasets/davidscripka/openwakeword_features. Dataset license: CC BY-NC-SA 4.0. This run uses portions of the false-positive validation dataset as training negatives and reserves disjoint portions for validation and test. It does not claim results against the full untouched upstream validation benchmark. The resulting baseline is intended for personal experimentation; commercial deployment requires reviewing/replacing the noncommercial training assets.
- Official automatic training notebook and config are saved as `upstream_training.ipynb` and `upstream_config.yml` for reference: https://github.com/dscripka/openWakeWord.
