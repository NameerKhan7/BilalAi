# Hey Bilal — training results

The custom model has been trained and exported to `models/hey_bilal.onnx`.

The second revision adds shifted examples of similar phrases and silence to reduce streaming false triggers. Its original benchmark used threshold 0.48 with single-frame triggering; the current runtime policy below supersedes that setting.

| Final check | Result |
|---|---|
| Fresh synthetic wake phrases | Detected 40 out of 40 |
| Fresh synthetic similar phrases | False trigger on 1 out of 40 |
| Held-out background feature windows | False positive on 70 out of 6,685 (1.05%) |
| ONNX export compatibility | Passed |
| Your voice and actual room | Not tested yet |

The fresh phrase test uses speakers 560–599, outside the training and calibration voices. Background windows are sampled without overlap from a held-out partition. Their error rate does not measure real-world false activations per hour.

**Status: trained personal-use baseline. Background false triggers remain too frequent to call this ready for reliable always-on use.**

Double-click `test_wakeword.bat` in the `code` folder to run a 60-second local microphone test. Say “hey Bilal” ten times at different distances, then try ordinary speech and similar phrases. The test processes audio locally and does not record or upload it.

The detailed metrics are in `training_report.json`; the reproducible training steps and source licenses are in `README.md`. Some training assets have a noncommercial license, so commercial deployment requires a different licensed dataset or further license review.


## Current detection policy ? hee-haa false-trigger correction

The runtime now uses threshold **0.80** and requires **two consecutive 80 ms frames** above it. One continuous match produces one detection; a low score rearms the gate, with a 0.6-second cooldown. Raw peak scores are shown separately from confirmed scores.

The user reported hee-haa triggers at 0.562, 0.662 and 0.711, and genuine detections at 0.835 and 0.966. This threshold rejects those reported false-trigger levels. It still requires a fresh microphone test to verify both rejection and genuine recognition with the new temporal rule.

Replay checks at the new policy detected 20/20 synthetic wake phrases, 0/20 synthetic hee-haa sounds, and 0/10 other similar phrases. These are focused regression checks, not a guarantee about real voices or continuous background audio. Detailed scores are saved in `wakeword_policy_report.json`.

Model weights are unchanged. A synthetic hee-haa negative corpus and its extracted features are prepared in the ignored training cache, and the trainer can incorporate them if retraining is needed after a real microphone retest. The CPU-heavy preparation job has finished.

## Repeat-delay correction

A replay containing five wake phrases with half-second gaps produced only three detections with the old two-second cooldown, and five detections with the new 0.6-second cooldown. The model is warmed up before the microphone-ready message, and live capture requests the lower input-latency setting. Median processing in replay was approximately 3-4 ms per 80 ms audio block.

The existing synthetic rejection check still passed: 20/20 wake phrases detected, no triggers on 20 hee-haa clips or 10 other similar phrases. Actual microphone timing and recognition need retesting. The terminal now prints microphone latency and processing times, making a hardware backlog distinguishable from a missed phrase. See `repeat_latency_report.json`.
