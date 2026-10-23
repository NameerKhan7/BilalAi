# Testing and acceptance

[Documentation home](README.md) · [Troubleshooting](troubleshooting.md) · [Detailed field checklist](FIELD_ACCEPTANCE.md)

Bilal needs both repeatable software tests and real use on the target PC. A mocked send is not a delivered email, an installed speech engine is not an audible reply, and a configured startup shortcut is not a successful sign-in run.

**Prior recorded regression:** 154 automated tests passed on **23 October 2026** with native Windows support. See the capability-build validation section below for newer evidence. These cover simulated audio/providers and mocked external effects. Live Gmail/Notion acceptance, fresh physical voice/background-media testing, real keyboard/microphone acceptance, and sign-in acceptance remain pending.

## Run the regression suite

From the project root, using its virtual environment:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -q
```

The hold/session tests cover endpoints, modifier-state edges, UI presence, release, default no-auto-follow-up behavior, release hiding, spoken clarification, and speech/input/approval interactions. Native microphone/hotkey acceptance remains separate.

The suite uses simulated providers and side effects. It should not be treated as permission to send mail, create live account content, or power off the PC. Select relevant tests during development, then run the full suite for changes that cross the controller, agent, tool, or approval boundaries.

## Run local readiness checks

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py
```

To include the suite in the same readiness report:

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py --tests
```

The report is saved to the private `logs/mvp_readiness.json`. It checks local microphone format support, available speech engines, startup shortcut targets, wake verifier file presence, valid reviewed example counts, and credential-file existence. It makes no Gmail/Notion API calls, records no microphone audio, and trains no model.

Read the report's individual statuses. `stored_not_verified`, `configured`, and `format_supported` have narrower meanings than full end-to-end success. Verifier file presence does not itself establish successful inference or model checksum verification at runtime.

## Test ownership map

| Test files | Main behavior covered |
| --- | --- |
| `test_agent_core.py`, `test_agent_loop.py`, `test_request_router.py` | Agent reasoning/dispatch contracts, tool results, and request forwarding. |
| `test_desktop_worker.py`, `test_spotify.py` | Accessible desktop observations, stale controls, guarded actions, and playback handling. |
| `test_audio_capture.py`, `test_stt_client.py` | Speech endpoint behavior, recording format, transcription inputs, and safe provider failures. |
| `test_wake_acceptance.py`, `test_wake_activation.py` | Wake policy, verified activation, final trigger checks, and rejection paths. |
| `test_ui_controller.py`, `test_acceptance_flow.py`, `test_contextual_input.py`, `test_conversation.py` | Request lifecycle, missing input, cancellation, and approval handoffs. |
| `test_business_learning.py`, `test_power_tools.py` | Account/memory workflows, reviewed learning, and confirmed power behavior with simulated effects. |
| `test_background_startup.py`, `test_paint_shutdown.py`, `test_mvp_voice_web.py` | Hidden startup, cleanup, and voice/web behavior. |

The executable assertions remain the source of truth for exact coverage. A filename does not promise all possible app versions or failure conditions are tested.

## Physical acceptance sequence

Quit any previous instance from its tray menu and launch the updated app. Record actual outcomes for the following scenarios, including the distance/noise conditions.

| Scenario | Expected result |
| --- | --- |
| Launch without speaking | One tray instance; companion hidden. |
| Ordinary speech/music or YouTube without the trigger | No companion activation and no agent task. |
| “hey” alone, “hee haa,” or similar non-trigger sounds | No activation. |
| Full “Hey Bilal” followed immediately by a harmless question | Activation, first words preserved, complete answer aloud, then hidden without automatic follow-up capture. |
| After a reply, speak without wake/hold/manual activation | No automatic new command recording. |
| Hold Ctrl + Shift + Space, pause over4s, continue, then release | Capture survives the thinking pause; release submits once and hides immediately; background processing/audio continue without reopening the mic. |
| Hold/release during TTS, input, or approval | No self-recorded reply; no shortcut submission or approval of dialogs; no duplicate capture. |
| Dictated request with a three-second thinking pause | Command continues across the pause. A pause over four seconds may end capture by design. |
| Missing city/country | Spoken clarification with no text dialog; hold-to-talk or verified wake answer resumes the original lookup. |
| Quiet prayer lookup | Confirmed city/date/method yields sourced calculated start times, no browser tabs, bounded retries or a clear blocker. |
| Click avatar during processing or SAPI speech | Click ignored; no extra recording or task. |
| Missing email recipient | Contextual input appears; invalid address does not continue; cancellation stops the request. |
| “never mind” during a harmless processing request | Stops subsequent work. Completed actions cannot be undone. |
| Wake listening disabled in the tray | Full phrase does not automatically activate the companion. |
| Network unavailable during a harmless request | A clear failure; no false claim of completed work. |
| Sign out and back in after startup installation | One background instance; hidden until activated; wake and speech work. |

Repeat the positive and negative wake tests with background playback and different distances. Media actually saying “Hey Bilal” can still trigger this version; it has no speaker identification or playback echo cancellation. The [field checklist](FIELD_ACCEPTANCE.md) gives the detailed sequence.

For a real app task, inspect its final state. “Opened Spotify” is insufficient for “play this song”; verify the requested song and artist are actually playing.

## Diagnose the classifier separately

These commands deliberately listen to the microphone. Stop the running assistant or disable its wake monitor first to avoid sharing the device:

```powershell
.\venv\Scripts\python.exe .\wakeword.py --list-devices
.\venv\Scripts\python.exe .\wakeword.py --seconds 60
```

`wakeword.py` tests the acoustic classifier and temporal score policy. It **does not test the GUI's full offline phrase-verification gate**, final command trigger check, transcription, agent, or spoken output. A high score is a candidate, not proof that the full app will activate. The live monitor now uses `candidate_threshold=0.30` before full local phrase verification, whereas this standalone diagnostic retains `threshold=0.80`. This policy change is not a new trained model or an accuracy claim. Its threshold/frame flags are diagnostic overrides for that process, not automatic deployed-policy changes.

## Reviewed wake-learning workflow

Use **Collect reviewed wake examples** in the tray. It pauses monitoring while the guided collector owns the microphone. Each clip is played locally; confirm only correct labels. Do not mark a mispronounced or clipped phrase as a successful full trigger.

The command-line equivalent is:

```powershell
.\venv\Scripts\python.exe .\collect_wake_examples.py --label both --count 10
```

Run collection again in a separate session with different distance/noise. Preparation requires at least ten valid reviewed positives, ten valid reviewed negatives, and two sessions each containing at least two of each class. Missing or modified clips fail hash review and are excluded. Include “hey” alone, confusable words, and normal speech as negatives.

```powershell
.\venv\Scripts\python.exe .\evaluate_wake_learning.py
.\venv\Scripts\python.exe .\train_reviewed_wake.py
```

Evaluation scores the deployed acoustic classifier/policy and writes `data/wake_examples/evaluation.json`; it does not benchmark the complete phrase-verification cascade. Preparation copies reviewed examples into a private training session and creates a candidate output plan. It does not train unless requested:

```powershell
.\venv\Scripts\python.exe .\train_reviewed_wake.py --train-candidate
```

Candidate training also needs the underlying training script's feature/data assets. Outputs stay under `models/candidates/`; no deployed model is automatically replaced. Validate with fresh independent microphone recordings, compare misses and false activations, and rerun end-to-end field acceptance before considering promotion. [Voice calibration](../training/VOICE_CALIBRATION.md) provides additional historical training context.

## Account and power acceptance

Live Gmail and Notion tests are intentionally pending until the user configures and authorizes them. Codex's account connections do not connect the standalone app. Follow [connection setup](getting-started.md) and the [account acceptance sequence](FIELD_ACCEPTANCE.md).

For Gmail, first reject a deliberate test draft and verify no send occurred; then review and approve a fresh draft to a chosen test recipient. Verify delivery. A changed draft requires a fresh review. If a send result is uncertain, inspect Sent before retrying.

For Notion, start with a requested read of a shared test page, then deliberately request a test note under the chosen parent and compare title/body with readback.

Power effects in automated tests are mocked. An actual sleep/restart/shutdown test interrupts the PC and belongs to a deliberate user-controlled session with work saved. Approval acceptance is not proof that hardware or Windows completed the effect. While asleep, Bilal cannot hear a wake phrase.

## Interface preview

```powershell
.\venv\Scripts\python.exe .\main.py --preview-all
```

This renders character states to the ignored `ui_preview/` folder without microphone or provider usage. Inspect the output for clipping, state differences, readability, and character/orb placement. It is not a test of live audio or task execution.

## Record evidence consistently

For each field check, record the date, app/version, exact request, expected result, observed result, pass/fail, and any relevant redacted trace reference. Keep raw recordings and account details private. Do not turn pending checks into “passed” because related unit tests succeeded.

## Wake replay evidence — 23 October 2026

The first-candidate audio-window replay, including the classifier gate and local verifier, accepted 8 of 10 historical positive-labelled recordings after the candidate threshold/context/confidence changes, compared with 2 under the old streaming settings. One historical positive label is the user-reported wrong phrase “hey Bill”; these labels are not a clean accuracy dataset. None of 13 historical negatives or 9 resampled synthetic negatives activated. A synthetic positive did not activate, so recall is still imperfect.

Full-file verifier checks and candidate-window checks are different: the verifier alone accepted one historical negative after this recalibration, while the classifier prevented that clip from activating. Both gates remain necessary. Do not describe these results as zero false activations in general, speaker identification, or fresh YouTube/microphone acceptance. The live shortcut and normal-distance wake tests below remain necessary.

A harmless live Gemini assignment prompt produced a relevant English clarification about the assignment topic with desktop/account tools disabled. This checks one conversational example, not every follow-up or humor response.

## Research regression checks

Check quiet search and prayer adapters with fake HTTP responses, including blocked RSS, empty results, wrong date, incomplete timing data, repeated calls, and exhausted per-run budgets. A blocked 102-character Google error response must not become verified research evidence. Live-source availability and physical microphone behavior need separate evidence. Inspect trace timing/counters and partial checkpoints when diagnosing slow tasks; a provider HTTP error is different from a blocked source response. The latest 154-test run covers these regression checks; live-source and physical acceptance still require their own evidence.

## Latest research evidence — 23 October 2026

The latest validation run passed 154 automated tests on native Windows. A live Bing RSS search returned usable results. A live Gemini Fajr request used one `prayer_times` call with zero browser-opening attempts and answered **4:57 AM for Wah Cantt on 23 October 2026**, stating the Karachi calculation method and distinguishing prayer start from congregation time. This is evidence for that single city/date/run, not a standing current prayer time or proof of every location/method.

The earlier city-name endpoint returned unrelated coordinates; the current coordinate flow resolves the settlement independently and checks returned coordinates, date and method. Regression fixtures reject mismatched coordinates and invalid/ambiguous location responses. Live Gmail/Notion delivery, physical microphone/hotkey use, and real power transitions remain separate acceptance work.

## Capability-build validation — 23 October 2026

The confirmed full native Windows suite passed **195 tests in 22.078 seconds on 23 October 2026**, including screen/DOM and deterministic-plan regression checks. Do not infer completion of all P0 requirements from a test count. The [capability matrix](CAPABILITY_STATUS.md) tracks 138 specification items and distinguishes code, automated evidence, live evidence, and missing acceptance. Start with [Task system](task-system.md) for the new runtime.

Evidence recorded by the implementation work:

- Gemini/Groq provider keys were moved to Windows Credential Manager with verified readback. No credential values belong in test evidence.
- Global keyboard-hook registration/release passed a native check. This is not physical 50-trial shortcut, latency, or microphone acceptance.
- A real Gemini queued answer and a real read-only Codex answer completed. Claude 2.1.309 was installed and help inspected, but `ANTHROPIC_API_KEY` is missing, so a live Claude task was not validated.
- A native 100,000-byte clipboard roundtrip was verified and the original clipboard restored. This is one payload-size check, not every content type or application.
- The owned Chrome session opened and read `example.com`, `www.python.org`, `docs.python.org`, `en.wikipedia.org`, and `www.wikipedia.org`. This establishes public opening/reading only, not safe form execution across five sites.
- Screen picker, indicator, overlap guard, daily cap, and pointer interception have code/test paths. No actual screen capture was submitted during this work; 20-element safe OS pointer acceptance remains pending.

Use these additional deliberate acceptance checks:

1. Confirm wake is off on a fresh/default launch and cannot be enabled without the fresh independent acceptance gate. The gate needs50 positive trials with at least 90% true activations and one hour of negatives with fewer than one false activation/hour, dated within 30 days.
2. Hold the default **Ctrl+Shift+Space**, speak, release, and expect one queued task with immediate avatar hiding. Test Settings remapping/toggle after restart. Verify **Ctrl+Alt+Backspace** stops pending/running work and capture without claiming rollback of completed effects.
3. Queue another harmless request while earlier task work runs. Inspect durable task state, steps, artifacts, cancellation, interrupted recovery, and exact reviewed-step continuation. Resume must not rerun unrelated completed writes.
4. Put an exact non-secret payload in Quick Input, reference it in an instruction, and verify byte-preserving output and stored non-secret snippet behavior. For a secret fixture, verify model context/history/artifacts use masked slots and no reusable plaintext snippet is created. Use test values, never real credentials in test output.
5. In dry-run, confirm no backend mutation. Exercise out-of-root paths, private directories, stale approvals, changed exact arguments, and secret-bearing/`.env` L2 approvals with fixtures. Verify controlled-write readback and version restoration within an allowed test folder.
6. Exercise screen picker cancellation without a capture; then, only when deliberately ready to share a chosen harmless screen, validate the indicator, sensitive-window rejection, no stored screenshot file, and answer-only behavior. Treat physical pointer, mixed-DPI, fullscreen, and secure-desktop tests as separate pending checks.

OS read isolation, approved write-mode headless delegation, benchmark 50, seven-day dogfooding, account delivery, and the complete P0 acceptance set remain unfinished. Unit/contract tests and the listed live checks do not close those gaps.

Deterministic-plan regression includes one approval for up to 20 typed calls, edited-plan invalidation, stop-on-first-failure behavior, no replay of earlier steps, non-secret plan recovery for later review, and global-stop approval revocation. Dynamic UI batches and approved external-agent writes remain outside the completed scope. The 195-test suite does not replace the 50-task semantic benchmark, real physical voice acceptance, or seven-day dogfooding.
