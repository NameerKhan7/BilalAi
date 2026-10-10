# BilalAI — 6-Week Build Roadmap (Solo Dev Edition)

**Goal:** A working Windows voice assistant — wake word → listen → transcribe → think → speak — running persistently in the background, styled with the BilalAI character states you've already designed.

Built in: **Python** • **VS Code**
Wake word: **openWakeWord** (custom-trained)
STT: **faster-whisper** (local, free)
Brain: **Claude API** (or local LLM fallback)
TTS: **Piper TTS** (local, free)

---

## Before You Start — One-Time Setup (do this in one sitting)

| Task | Time |
|---|---|
| Create a GitHub repo: `bilalai` — private is fine solo | 5 min |
| Set up a Python virtual environment (`venv` or `conda`), Python 3.11 or 3.12 recommended for max package compatibility | 10 min |
| Install core deps: `pyaudio` or `sounddevice`, `openwakeword`, `faster-whisper`, `piper-tts` | 15 min |
| Sign up: `console.anthropic.com` (Claude API key) | 5 min |
| Create a `.env` file for API keys — add to `.gitignore` immediately | 5 min |
| Create a `config.py` or `.yaml` for wake word threshold, mic device index, voice settings | 10 min |
| Test your mic input device works in Python (`sounddevice.query_devices()`) | 5 min |

### GitHub Branch Strategy (even solo, keeps you sane)
| Branch | Purpose |
|---|---|
| `main` | Only working, tested code |
| `feat/wake-word` | Wake word training + detection |
| `feat/stt` | Speech-to-text integration |
| `feat/brain` | Command routing / LLM logic |
| `feat/tts` | Text-to-speech integration |
| `feat/ui-states` | Wiring the 8 BilalAI expression states to app states |

Daily ritual: commit at the end of every session, even if it's not "done." Never leave uncommitted work overnight.

---

## Week 1 — Wake Word Finalized

**Done = "hey bilal" reliably triggers a detection event on your own voice, in a normal room, with an acceptable false-positive rate.**

| Task | Notes |
|---|---|
| Finish training run in Colab (GPU runtime) | `piper-phonemize-fix`, Python 3.13-compatible |
| Download exported `.onnx` model | Rename clearly: `hey_bilal.onnx` |
| Write a local test script using `openwakeword` to stream mic input and print detection confidence | ~30 lines |
| Test in a normal room with background noise (TV, typing, talking) — not silence | Real-world accuracy |
| Tune detection threshold (start at 0.5, adjust up/down) | Balance false triggers vs missed detections |
| Lock the model — stop tweaking after this week | Prevent scope creep |

---

## Week 2 — Core Listening Loop

**Done = a background Python process is always listening, and "hey bilal" flips it into a "listening" state — no STT yet.**

| Task | Notes |
|---|---|
| Build a continuous mic-streaming loop (`sounddevice` `InputStream` or `pyaudio`) | Runs at 16kHz mono, standard for wake word + STT |
| Feed audio frames into the openWakeWord model in the loop | Non-blocking |
| On detection: play a short "listening" chime/sound and set app state to `LISTENING` | UX cue |
| Add a simple state machine: `IDLE → LISTENING → PROCESSING → SPEAKING → IDLE` | Matches your 8-panel expression sheet states |
| Add basic logging (timestamp + confidence score per detection) | Debugging |
| Stress test: leave it running for a few hours, check for memory leaks or crashes | Stability |

---

## Week 3 — Speech-to-Text

**Done = after wake word triggers, your spoken command gets transcribed to text accurately.**

| Task | Notes |
|---|---|
| Integrate `faster-whisper` (base or small model — good speed/accuracy tradeoff on CPU) | Local, no API cost |
| Record N seconds (or until silence) after wake word triggers | Silence detection via simple energy threshold, or fixed 5-6s window to start |
| Feed captured audio into `faster-whisper`, get transcript | |
| Test transcription accuracy with your actual voice, accent, mic distance | Tune model size if accuracy is poor |
| Handle edge cases: no speech detected, background noise triggers false STT | |
| Print/log transcript to confirm pipeline works end-to-end (wake → listen → transcribe) | Milestone checkpoint |

---

## Week 4 — Command Routing + First Real Actions

**Done = 3-5 real commands work end-to-end: transcript in, useful action or answer out.**

| Task | Notes |
|---|---|
| Set up Claude API call: send transcript, get a response | Use a system prompt defining BilalAI's role/personality |
| Build a simple intent layer: hardcode 3-5 commands (open app, search web, tell time, general Q&A fallback to Claude) | Don't over-engineer — prove the loop first |
| Route: if hardcoded command matches → execute directly; else → send to Claude | |
| Add basic error handling (API timeout, no internet, unrecognized command) | |
| Set app state to `PROCESSING` while waiting on response | Matches expression sheet |
| Test all 5 commands multiple times each | |

---

## Week 5 — Text-to-Speech + Full Loop Closed

**Done = BilalAI talks back. Full loop: wake → listen → transcribe → think → speak.**

| Task | Notes |
|---|---|
| Integrate Piper TTS (local, free, decent quality) | Pick or generate a voice model |
| Convert Claude/command response text → speech → play through speakers | |
| Set app state to `SPEAKING` during playback, back to `IDLE` after | |
| Handle interruptions gracefully (what happens if wake word triggers again mid-speech?) | Decide: ignore, or barge-in |
| Full end-to-end test: 10 real interactions in a row | Note every friction point |

---

## Week 6 — Persistence, Polish, MVP

**Done = BilalAI runs quietly in the background, auto-starts, and visually reflects its state.**

| Task | Notes |
|---|---|
| Wire the 8-panel expression sheet states (idle, listening, processing, speaking, success, error, loading, inactive) into a small always-on-top overlay window | Tkinter/PyQt for a lightweight UI, or the BilalAI icon in the system tray |
| Set up auto-start on Windows boot (Task Scheduler or a startup shortcut) | |
| Add a system tray icon with quit/pause/settings options | `pystray` |
| Bug-bash: run it for a full day of normal use, log every false trigger, crash, or missed command | |
| Fix top priority bugs (anything that breaks the core loop = critical) | |
| Package as a `.exe` (optional, via PyInstaller) if you want a double-click install | Stretch goal, not required for MVP |
| **MVP done** — BilalAI listens, understands, and responds, running persistently on Windows | |

---

## Master Summary

| Week | Phase | Focus | End State |
|---|---|---|---|
| W1 | Wake Word | Train, test, tune | "hey bilal" reliably detected |
| W2 | Listening Loop | Background mic stream + state machine | Always-listening loop stable |
| W3 | STT | faster-whisper integration | Voice → accurate text |
| W4 | Brain | Claude API + command routing | 5 working commands |
| W5 | TTS | Piper integration | Full loop: wake → answer → speak |
| W6 | Polish | UI states, auto-start, bug-bash | MVP shipped |

---

## Free/Low-Cost Tools Used

| Tool | Purpose | Cost |
|---|---|---|
| openWakeWord | Wake word detection | Free, open-source |
| faster-whisper | Speech-to-text | Free, runs locally |
| Piper TTS | Text-to-speech | Free, runs locally |
| Claude API | Command understanding / general Q&A | Pay-per-use, small at this scale |
| sounddevice / pyaudio | Mic streaming | Free |
| pystray | System tray icon | Free |
| PyInstaller | Optional `.exe` packaging | Free |

---

**Non-negotiables:**
1. Commit at the end of every session.
2. Don't add new features mid-week — finish the week's "done" state first.
3. Test each week's milestone with your actual voice/mic/room before moving on.
4. Keep API keys out of the repo — `.env` + `.gitignore`, always.
