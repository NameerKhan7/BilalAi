# Configuration reference

[Documentation home](README.md) · [Setup](getting-started.md) · [Code reference](code-reference.md)

These are the settings the current code actually reads. Most behavior limits are code defaults rather than user-facing preferences. Restart Bilal after changing files or environment variables.

## Provider settings

The committed [.env.example](../.env.example) is the template; the real `.env` is private and ignored by Git.

| Name | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | None | Required for hosted answers and agent reasoning. |
| `GROQ_API_KEY` | None | Required for recorded-command transcription. Typed requests do not need it. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Overrides the model used by `AgentBrain`. Blank falls back to the default. |

For normal app usage, a process environment value takes precedence over the corresponding `.env` value. `AgentBrain(model=...)` can override the model in code; `transcribe_recording(..., api_key=...)` can override the transcription key for a direct caller. Those parameters are developer interfaces, not extra `.env` entries.

Groq's model is currently the `DEFAULT_MODEL` constant in `stt_client.py`: `whisper-large-v3-turbo`. It is not configured with `GROQ_MODEL`. Account tokens are handled separately through [connection setup](getting-started.md), not added to `.env`.

## Wake detector policy

[`config/config.yaml`](../config/config.yaml) contains **JSON syntax**, despite its filename. Preserve valid JSON when editing it.

| `wakeword` field | Current value | Runtime meaning |
| --- | --- | --- |
| `threshold` | `0.8` | Standalone classifier diagnostic/evaluation threshold. |
| `candidate_threshold` | `0.3` | Live monitor threshold before offline full-phrase verification; falls back to `threshold` if absent. |
| `consecutive_frames` | `2` | Consecutive 80 ms frames needed by the gate. |
| `cooldown_seconds` | `0.6` | Minimum repeat interval, combined with rearming after low scores. |

The GUI's `WakeMonitor` directly consumes `candidate_threshold` (falling back to `threshold`), `consecutive_frames`, and `cooldown_seconds`. Other entries such as `phrase`, `model_path`, `sample_rate`, `chunk_samples`, `status`, `microphone_latency`, and `warmup_silence_seconds` describe intended settings or provenance but are **not all dynamically wired into the GUI monitor**. In current code the stream is fixed at 16 kHz mono int16, 1,280 samples per block, and low latency; `load_detector()` defaults to `models/hey_bilal.onnx`. Editing `phrase` does not train or change the wake phrase.

Lowering a threshold can increase both sensitivity and false activation. Evaluate reviewed positive and negative recordings before changing policy; do not tune against a single successful utterance.

## Offline phrase verifier

These are constants and decoder arguments in [`wake_verifier.py`](../wake_verifier.py), not editable UI settings:

| Setting | Current value |
| --- | --- |
| Model location | `models/wake_asr/` |
| Model / execution | Whisper base.en, CPU int8, two CPU threads, one worker, local files only |
| Vocabulary context | `Hey Bilal.` |
| Minimum segment average log probability | `-0.60` |
| Maximum no-speech probability | Strictly below `0.6` |
| Decoder | English, beam size 1, temperature 0, no previous-text conditioning, no VAD filter |
| Accepted check-audio duration | 0.1–6 seconds |

The complete phrase must also be recognized; context alone is insufficient. Phrase matching searches the first 200 transcript characters so captured pre-roll is permitted. This is a context-biased recognition check, not speaker identification. A video containing the full trigger can still activate the assistant.

Before decoding, the verifier trims long silent margins using 20ms RMS blocks, retaining 160ms around the detected sound. This normalizes verification context without trimming the buffered command capture. The confidence cutoff was recalibrated to -0.60 against local replay; phrase and no-speech checks still apply.

The monitor retains 32 blocks of pre-candidate context and adds three blocks of lookahead before verification. Buffered command audio is bounded; excessively slow checks are rejected. See [Architecture](architecture.md) for the activation sequence.

## Recording defaults

[`CaptureConfig`](../audio_capture.py) defines these defaults. The controller removes the initial calibration interval for a wake-started capture because it reuses the active microphone stream.

| Field | Default | Meaning |
| --- | --- | --- |
| `sample_rate` / `block_ms` | 16,000 / 20 | Mono audio format and analysis block size. |
| `calibration_seconds` | 0.30 | Initial noise sampling for manual capture; zero on wake capture. |
| `pre_roll_seconds` / `tail_seconds` | 0.25 / 0.25 | Context retained around detected speech. |
| `silence_seconds` | 4.0 | Silence after speech that finishes capture. |
| `initial_wait_seconds` | 10.0 | Maximum wait for speech to begin. |
| `max_seconds` | 90.0 | Total capture limit. |
| `min_speech_rms` / `noise_multiplier` | 0.008 / 3.0 | Minimum speech level and noise-relative threshold. |
| `onset_frames` | 3 | Consecutive speech-level blocks needed to begin a command. |

New hold-to-talk and spoken-clarification captures override `max_seconds` to 600 and calibration to zero. Dormant internal follow-up mode uses a 15s initial wait, but default `AssistantWindow.conversation_enabled` is `False`; normal operation never automatically starts it. Hold/clarification mode starts with 10 but suppresses no-speech and silence endpoints while the keys remain held. Ordinary capture remains 90s/10s/4s. Release requests manual finish, and the 600s bound can process a chunk before release.

`conversation.py` defines `FOLLOWUP_WAIT_SECONDS=15.0`, exact whole-utterance conversation endings, and visibility presence. `hold_to_talk.py` polls only Windows left Ctrl (`0xA2`) and left Shift (`0xA0`) states every 25ms; it does not intercept or record typed keys. The shortcut has no current user-facing remapping setting. Hold release ends the session and hides the UI while processing/audio may continue. General `text` clarification can be recorded with hold-to-talk; an `email` field retains the paste dialog. Busy/speaking avatar clicks are ignored.

Silence detection measures sound level; it does not understand whether a sentence is complete. The guided wake-example collector deliberately uses shorter capture limits than regular commands.

## Behavior limits and controls

| Area | Current behavior | Owner |
| --- | --- | --- |
| Agent run | Up to 12 rounds, 180-second deadline, 20-second provider HTTP timeout | `agent_core.py` |
| Command transcription | 20-second provider timeout, one SDK retry, mono 16 kHz WAV up to 25 MiB | `stt_client.py` |
| Desktop worker | Bounded 20-second bridge call | `agent_tools.py` |
| Missing input | Spoken hold-to-talk text clarification, or single-line email paste dialog; validated details up to 2,000 characters | `contextual_input.py` |
| Power approval | Expires after 120 seconds | `power_tools.py` |
| Companion | 96 × 120 px by default | `main.py` |
| Tray controls | Wake listening and spoken replies can be toggled during use | `main.py`, `ui_controller.py` |

[`brand_theme.json`](../brand_theme.json) supplies brand colors and font. Character assets live in `assets/character/`; [asset notes](../assets/character/ASSET_NOTES.md) describe their origin and current animation limits.

## Private runtime files

Recordings, traces, learned preferences, approval state, account tokens, downloaded verifier weights, and candidate models are generated locally. Their locations and provider boundaries are described in [Data and security](data-and-security.md). Do not treat a token file's existence or a readiness status as proof of a live connection.

## Research budgets and location

`ResearchGuard` in `research_tools.py` permits per-run maxima of two quiet searches, three page reads, two browser openings, and two prayer lookups. Identical normalized tool/argument repeats are rejected. These are code limits, not `.env` options. Quiet Bing RSS search returns up to five leads. Research HTTP calls use 12s timeout, no redirects, and 256,000-byte response bound. Prayer calculation defaults to Aladhan method `1` (Karachi), with city, country, and ISO date required. No GPS/IP location detection or silent preferred-city saving is implemented. Confirmed memory and current context remain the available location sources.

Prayer location resolution uses Nominatim structured city/country search with up to three candidates. Matches must have the requested country and a settlement type; matches separated by more than 0.1 degrees require clarification. Production requests are serialized with one-second spacing and a 64-entry in-memory LRU cache. Aladhan receives the resolved coordinates through `/timings/DD-MM-YYYY`; return coordinates must match within 0.02 degrees, date and method ID must match, and timezone/Fajr must be present. The cache does not persist a preferred city, use GPS/IP, or automatically save memory. OpenStreetMap attribution is included in returned location metadata. Research streaming also has a 25-second total deadline in addition to the 12-second request timeout.
