# Calibrate with your actual voice

The live timing reported by the user (4.2 ms median, 6.0 ms p95 per 80 ms block; 80 ms input latency) shows the processor can keep up. It does not tell us how many spoken attempts were missed. Labeled recordings distinguish low model scores, brief single-frame matches, and microphone level issues.

From the code folder, run:

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py
```

Follow the Enter prompts. Say each requested phrase once, naturally, at your usual microphone distance: five `hey Bilal` recordings and five `hee haa` recordings. Each recording lasts three seconds. Wait for `SPEAK NOW` before speaking.

Recordings and analysis are saved locally under `training/recordings/session_<id>/`. This folder is excluded from Git. Nothing is uploaded. The tool diagnoses the current 0.80/two-frame policy and evaluates candidate thresholds and confirmation lengths; it does not apply a change. A candidate must be checked with a fresh separate session before use.

The report also includes raw scores, confirmed scores, audio volume, and clipping. If target and confusable scores overlap too much, changing only the threshold is insufficient; the real samples can guide further model training.

Reanalyze an existing session without recording:

```powershell
.\venv\Scripts\python.exe .\calibrate_wakeword.py --analyze-only "training\recordings\session_<id>"
```

The analysis path was tested using six existing synthetic clips. Live capture still requires running the guided command yourself.
