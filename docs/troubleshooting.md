# Troubleshooting

[Documentation home](README.md) · [Setup](getting-started.md) · [Testing](testing.md) · [Data and security](data-and-security.md)

Start with the stage that failed: activation → recording → transcription → reasoning → tool execution → spoken reply. Repeating the whole request can duplicate an action whose outcome was uncertain.

## No window appears

The normal launch is hidden. Look for Bilal's tray icon, including Windows' hidden-icon area. Use **Read reply / type a request** to open its details or start recording from the tray. If another instance already owns the lock, use that instance or quit it before restarting.

For startup troubleshooting, inspect the private `logs/background.log` and `logs/ui_startup.json`. The latter describes startup visibility, speech engine, and wake status. Do not post whole logs publicly without reviewing their content.

## “Hey Bilal” does not activate

1. Wake is off by default. Confirm a fresh independent acceptance report permits enabling **Listen for Hey Bilal** and the assistant is idle rather than waiting for missing input, approval, or a task.
2. Check the correct Windows microphone and microphone permissions. Test a manual recording from the tray to distinguish microphone trouble from wake trouble.
3. Run the local model installer, then quit and restart Bilal:

```powershell
.\venv\Scripts\python.exe .\setup_wake_verifier.py
```

4. Check wake status in `logs/ui_startup.json`. Missing verifier files or verifier failure disables automatic activation; manual requests remain available.
5. Test the full phrase at a normal distance. “hey” alone is intentionally insufficient.

The monitor retries temporary microphone failures with increasing delays up to ten seconds. A classifier diagnostic can isolate acoustic detection; see [Testing](testing.md). It does not exercise the whole activation gate. Collect reviewed examples if real utterances are repeatedly missed rather than immediately lowering thresholds.

## YouTube or other audio activates Bilal

The full application requires both a classifier candidate and local full-phrase verification, then checks the final command transcript before the agent runs. Ensure the old instance was quit and the updated app restarted.

Playback that actually contains the complete “Hey Bilal” phrase can still activate this version. There is no speaker identification or playback echo cancellation. Disable wake listening temporarily while investigating, review false-activation examples from the tray, and run the background-playback acceptance sequence in [Testing](testing.md). Never label an automatic detection as correct without listening to it.

## The companion or microphone stays active unexpectedly

Automatic follow-up listening is disabled by default. Release of a started hold capture should hide the companion immediately, with processing and the spoken answer continuing in the background. Ordinary wake/manual requests hide after reply completion. Busy or speaking avatar clicks are ignored. A waiting email/approval dialog is a separate interaction; an unresolved general question is answered explicitly with another hold-to-talk turn. Check that the updated instance is running before treating old 15s behavior as current.

## Global hold-to-talk does not behave as expected

Use the configured shortcut; the default is **Ctrl + Shift + Space** with left modifiers. Left Ctrl + left Shift alone works only if selected as a remap in Settings. Hold to record and release either key to submit. Wait for the listening state before speaking. The Windows hook tracks configured chord keys and forwards events; another app may also react. Restart after changing remap/toggle settings. It cannot approve a pending action or submit an email paste box. It can answer a spoken general clarification, such as city/country, while preserving the original task. If an existing task is processing, holding is not an immediate second queued request.

A new hold capture suppresses silence/no-speech endpoints while held, but has a 600s chunk bound. An already running ordinary wake/manual capture keeps its original 90s maximum. Reaching a bound can begin processing while still held without hiding the companion.

## Recording stops during a thinking pause

The current endpoint ends capture after **four seconds of silence** following speech; it cannot infer whether you intended to continue. It waits up to ten seconds for initial speech and caps a command at ninety seconds. A three-second pause should normally fit, but low microphone level can make quiet speech resemble silence.

Check distance/input level and the saved transcript before assuming the model ignored words. Recording defaults are in [Configuration](configuration.md). For a longer pause, use global **Ctrl + Shift + Space** hold-to-talk and release to submit. Its held endpoint suppresses the ordinary silence stop; maximum capture bounds still apply.

## Transcription gets an app or song name wrong

Inspect the saved command transcript, not just the spoken answer. Try a specific natural phrase such as “Chrome browser” or a song title plus artist. The transcription prompt contains app vocabulary and confirmed `alias.` / `pronunciation.` memories, but this does not guarantee recognition.

Avoid blanket text substitutions: a real word could be corrupted. If the transcript was correct but the action was wrong, investigate the agent trace/tool result instead of changing speech recognition.

## Transcription fails

A missing/rejected Groq key, unavailable quota, timeout, or network failure produces a user-facing error. Check the Groq key in Settings/Windows Credential Manager and the provider account's quota without exposing the key. Use the project's virtual environment and [setup instructions](getting-started.md).

The supported input is the recorder's nonempty mono 16 kHz, 16-bit WAV, up to 25 MiB. Unrelated audio formats should not be passed directly to the transcription function. A typed request can help isolate transcription from reasoning.

## A typed request also fails

Check the Gemini key in Settings/Windows Credential Manager, optional `GEMINI_MODEL`, network access, and provider quota. Process environment overrides Credential Manager, which overrides legacy `.env`, so an old process value can override a corrected stored credential. Restart after changing configuration.

The agent has bounded rounds/timeouts; a long or repeatedly blocked task may stop without completing. Read the relevant private task trace for the actual failed stage.

## An app opens but the requested task is incomplete

Launching, searching, and completing the goal are different outcomes. Check the final visible app state and `logs/agent_latest.json` for tool observations and returned errors.

Desktop control depends on Windows accessibility support and the installed app version. Some custom-rendered interfaces expose no useful controls. The generic desktop tool invalidates observed control IDs after actions; it must inspect again before acting. Protected operations are deliberately blocked in generic controls. There is no arbitrary model-generated command executor or general screenshot-vision fallback.

For Spotify, verify actual playback and artist. Search results alone are insufficient. If the song is wrong, preserve the exact transcript and playback result when reporting the issue.

## No spoken reply

Enable **Speak replies** in the tray. Check the default Windows output device, volume, and installed speech voices. A readiness report listing a speech engine proves availability, not audibility. Use a harmless question and confirm sound through the intended speakers or headphones.

If speech was interrupted, check whether a cancellation or another UI interaction stopped it. Cancellation does not undo completed app actions.

## The missing-detail box is waiting

For an email address, paste the requested detail and press **Enter** or **Continue**. For a general spoken question, hold the configured talk shortcut (default Ctrl+Shift+Space), say the answer, and release; no text popup is expected. The current input is single-line, limited to 2,000 characters. An email request requires a complete address; a person's name alone is insufficient. Cancel or Escape ends this pending continuation.

Providing an address resumes draft preparation. It does not approve sending; the exact email must still be reviewed separately.

## Gmail or Notion is unavailable

Complete Bilal's own [account setup](getting-started.md). A Codex connection or Gemini key does not grant standalone account access.

For Gmail, use a Google **Desktop** OAuth client, enable the Gmail API, and complete consent locally. For Notion, share the intended page with the integration and ensure it has the needed permissions. A stored credential file is not proof of a valid connection. Live account acceptance remains pending until deliberately performed.

If an email send has an uncertain result, inspect Gmail Sent and the recipient before trying again. Do not approve the same content repeatedly as a connectivity test. A changed draft needs a new exact-content review.

## Approval or power request fails

Review the current pending action through Bilal's approval UI. The model cannot approve its own action. Approvals are one-use; stale, changed, previously claimed, or uncertain actions must not be silently replayed. Power approvals expire after two minutes.

Windows permissions, unsaved work, application behavior, and hardware sleep support can prevent a power request. The implementation does not force apps closed. A returned request-accepted state is not confirmation that the PC shut down, restarted, or slept. Bilal cannot listen while the laptop is asleep.

## It does not start after sign-in

Run `startup_windows.py` again from the current installed project location. The shortcut targets that environment's `pythonw.exe` and `launch_bilal.pyw`; moving either path can break it. Use `check_mvp_readiness.py` to inspect shortcut configuration, then deliberately sign out and back in to test the actual behavior. Startup occurs after sign-in, not before it.

## Paint warnings appear when exiting

Use **Quit Bilal** or Ctrl+C during a console launch, then check whether the current process exits cleanly. Shutdown code stops animation/speech/timers on the GUI path to avoid painting during teardown. If `QPainter` warnings persist in the updated version, report the exact warning, launch method, and whether a preview or ordinary UI was active; do not infer a model-training failure from a rendering warning.

## Useful private evidence

| File or folder | What it helps explain |
| --- | --- |
| `logs/ui_startup.json` | Startup state, visibility, and wake/speech readiness. |
| `logs/background.log` | Silent-launch diagnostics and Qt messages. |
| `logs/agent_latest.json` and `logs/agent_*.json` | Agent steps, observations, and tool results. |
| `recordings/command_*.wav` / `.txt` / `.answer.txt` | Captured command, transcription, and answer when saved. |
| `logs/mvp_readiness.json` | Local prerequisite checks and optional test result. |

These can contain private requests, addresses, page content, and observations. Report only a redacted relevant excerpt plus date, Windows/app versions, exact reproduction steps, expected behavior, and observed result. Never include credentials or account token files.

## Research takes too long or opens unrelated pages

Factual questions should use quiet search/public reading or the prayer-time adapter, not open browser tabs unless asked. Search may be blocked; snippets or access/error pages do not verify a changing fact. Code limits each run to two searches, three reads, two browser openings, and two prayer lookups, with identical repeats blocked. Check private trace counters, per-step elapsed time, model rounds, provider HTTP status, and partial checkpoints to identify provider delay versus source failure.

Prayer lookup requires confirmed city, country, date, and method; no GPS/IP location is inferred. If city is missing, answer the spoken clarification through hold-to-talk or “Hey Bilal” followed by the answer. Aladhan returns calculated starts, not the local mosque congregation schedule. Do not treat preferred-location memory as automatically saved unless its proposal was approved.

## Summarize a task without rerunning it

```powershell
.\venv\Scripts\python.exe .\diagnose_task.py --latest
.\venv\Scripts\python.exe .\diagnose_task.py --file "C:\path\to\agent_trace.json"
```

This reads a local saved trace only; it makes no provider calls and replays no actions. The default output summarizes model rounds, elapsed time, provider HTTP code, tool counts, repeats, unreadable pages, and per-step status/timing. Older traces may lack the newer timing fields. A 429 provider code indicates quota/rate limiting; an unreadable page is a source failure, not verified evidence.

Add `--details` only for local investigation: it prints the private request, outcome, and tool arguments. Review and redact before sharing any output. Default output reduces content exposure but still includes filenames, timestamps, model names, and activity metadata.

## Wake remains disabled despite installed models

That is the current default and acceptance policy. Model files, saved-clip replay, and a configured microphone do not satisfy the gate. A report must record at least 50 independent positives at 90% or better activation, at least one hour of negatives with fewer than one false activation/hour, and a timestamp within 30 days. Use the configured talk shortcut until proper field acceptance is recorded; do not manufacture a passing report from unit tests.

## Provider migration or Claude delegation fails

Use Settings to save a provider key or move legacy `.env` entries into Windows Credential Manager. Each stored key is read back before migration blanks its source entry. The fallback still exists; do not restore plaintext keys just because `.env` entries are blank. Credential access is tied to Windows account storage, not a universal encrypted database.

Claude requires `ANTHROPIC_API_KEY` for its isolated bare invocation. An installed Claude CLI and a successful `--help` call do not establish an authorized task. The recorded live delegation check currently covers read-only Codex and a Gemini queue answer; approved write-mode delegation and OS read isolation remain incomplete.

## A task is queued, blocked, or interrupted

Open **Tasks, history and settings**. Inspect the selected task's steps, result artifacts, and approval card. A blocked policy action may need an allowed folder/domain or an exact review; it should not be bypassed by asking another tool. On process restart, interrupted work needs explicit resume. Never repeat an uncertain external write before checking its real outcome.

Use **Ctrl+Alt+Backspace** for global stop. It cancels work/capture, not completed filesystem, browser, or account changes. New task records and artifacts live in SQLite; the older `diagnose_task.py` reads JSON agent traces and is not a replacement for Task Center when the queued runtime disables those traces.

## Owned browser cannot reach a page

Add the exact hostname in Settings, including every required public subresource/redirect host where appropriate. The Playwright session has its own `data/browser-profile/`; it does not attach your personal Chrome profile. Public navigation/read success does not prove login or form completion. Authentication, submission, upload/download, purchase, and destructive controls are blocked; stale element IDs require a fresh read.

## Screen question is blocked or unavailable

Start the explicit picker from the tray, choose a harmless scope, and check the visible capture indicator. Sensitive-window title/process overlap, the 20/day cap, cancelled picker, or expired memory-only frame can block capture. Minimize sensitive content or request a fresh capture; do not disable privacy checks to force it through. Images are not saved, but a textual answer/artifact can persist. No local OCR engine or complete 20-element physical pointer acceptance exists; fullscreen, secure-desktop, and mixed-DPI behavior still need validation.

For implementation/acceptance distinctions, use the [capability matrix](CAPABILITY_STATUS.md) and [task-system guide](task-system.md).

## An edited or restarted plan needs review again

Editing a deterministic plan invalidates the previous approval. Review the replacement plan rather than retrying the old ID. A batch contains at most20 typed file/contact/project/schedule calls; dynamic UI/DOM controls are excluded. On a failed/unverified step the plan stops; inspect the completed effects before creating another request, because earlier steps are not replayed automatically.

Normal quit preserves waiting non-secret plans and marks active work interrupted. After restart, review the pending plan; expired RAM secret slots need a fresh paste and approval. Global stop all revokes both policy and business pending approvals, so it intentionally differs from normal quitting. No write-mode external-agent batch is available.
