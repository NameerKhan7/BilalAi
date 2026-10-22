# Troubleshooting

[Documentation home](README.md) · [Setup](getting-started.md) · [Testing](testing.md) · [Data and security](data-and-security.md)

Start with the stage that failed: activation → recording → transcription → reasoning → tool execution → spoken reply. Repeating the whole request can duplicate an action whose outcome was uncertain.

## No window appears

The normal launch is hidden. Look for Bilal's tray icon, including Windows' hidden-icon area. Use **Read reply / type a request** to open its details or start recording from the tray. If another instance already owns the lock, use that instance or quit it before restarting.

For startup troubleshooting, inspect the private `logs/background.log` and `logs/ui_startup.json`. The latter describes startup visibility, speech engine, and wake status. Do not post whole logs publicly without reviewing their content.

## “Hey Bilal” does not activate

1. Confirm **Listen for Hey Bilal** is enabled and the assistant is idle rather than waiting for missing input, approval, or a task.
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

## The companion stays visible after the answer

This is an active conversation, not necessarily a stuck request. After spoken output finishes, Bilal waits 15s for another utterance without a new wake phrase. Say “we are done” or “stop listening,” cancel, or let that no-speech window expire. A held shortcut keeps it visible. Captured follow-up speech goes to Groq/Gemini; keep background playback in mind. No new full-command capture should run during TTS or approval/input dialogs.

## Global hold-to-talk does not behave as expected

Use **left Ctrl + left Shift**, not the right-side modifiers. Hold to record and release either key to submit. Wait for the listening state before speaking. The shortcut is state polling, not interception; another app may also react to its modifiers. It cannot approve a pending action or submit the missing-detail box. If an existing task is processing, holding is not an immediate second queued request.

A new hold capture suppresses silence/no-speech endpoints while held, but has a 600s chunk bound. An already running ordinary wake/manual capture keeps its original 90s maximum. Reaching a bound can begin processing while still held without hiding the companion.

## Recording stops during a thinking pause

The current endpoint ends capture after **four seconds of silence** following speech; it cannot infer whether you intended to continue. It waits up to ten seconds for initial speech and caps a command at ninety seconds. A three-second pause should normally fit, but low microphone level can make quiet speech resemble silence.

Check distance/input level and the saved transcript before assuming the model ignored words. Recording defaults are in [Configuration](configuration.md). For a longer pause, use global **left Ctrl + left Shift** hold-to-talk and release to submit. Its held endpoint suppresses the ordinary silence stop; maximum capture bounds still apply.

## Transcription gets an app or song name wrong

Inspect the saved command transcript, not just the spoken answer. Try a specific natural phrase such as “Chrome browser” or a song title plus artist. The transcription prompt contains app vocabulary and confirmed `alias.` / `pronunciation.` memories, but this does not guarantee recognition.

Avoid blanket text substitutions: a real word could be corrupted. If the transcript was correct but the action was wrong, investigate the agent trace/tool result instead of changing speech recognition.

## Transcription fails

A missing/rejected Groq key, unavailable quota, timeout, or network failure produces a user-facing error. Check `GROQ_API_KEY` locally and the provider account's quota without exposing the key. Use the project's virtual environment and [setup instructions](getting-started.md).

The supported input is the recorder's nonempty mono 16 kHz, 16-bit WAV, up to 25 MiB. Unrelated audio formats should not be passed directly to the transcription function. A typed request can help isolate transcription from reasoning.

## A typed request also fails

Check `GEMINI_API_KEY`, optional `GEMINI_MODEL`, network access, and provider quota. Environment variables override `.env` values, so an old process value can override a corrected local file. Restart after changing configuration.

The agent has bounded rounds/timeouts; a long or repeatedly blocked task may stop without completing. Read the relevant private task trace for the actual failed stage.

## An app opens but the requested task is incomplete

Launching, searching, and completing the goal are different outcomes. Check the final visible app state and `logs/agent_latest.json` for tool observations and returned errors.

Desktop control depends on Windows accessibility support and the installed app version. Some custom-rendered interfaces expose no useful controls. The generic desktop tool invalidates observed control IDs after actions; it must inspect again before acting. Protected operations are deliberately blocked in generic controls. There is no arbitrary model-generated command executor or general screenshot-vision fallback.

For Spotify, verify actual playback and artist. Search results alone are insufficient. If the song is wrong, preserve the exact transcript and playback result when reporting the issue.

## No spoken reply

Enable **Speak replies** in the tray. Check the default Windows output device, volume, and installed speech voices. A readiness report listing a speech engine proves availability, not audibility. Use a harmless question and confirm sound through the intended speakers or headphones.

If speech was interrupted, check whether a cancellation or another UI interaction stopped it. Cancellation does not undo completed app actions.

## The missing-detail box is waiting

Enter or paste the requested detail and press **Enter** or **Continue**. The current input is single-line, limited to 2,000 characters. An email request requires a complete address; a person's name alone is insufficient. Cancel or Escape ends this pending continuation.

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
