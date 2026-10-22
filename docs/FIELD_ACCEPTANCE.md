# Bilal field acceptance

[Documentation home](README.md) · [Testing guide](testing.md) · [Troubleshooting](troubleshooting.md)

Updated 2026-10-11, Asia/Karachi. Local regression tests and simulated account effects do not replace these checks. Physical speech, sign-in and account workflows are still pending.

## Run the local readiness report

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py --tests
```

This verifies the test suite, microphone format support, available speech engines, persisted startup shortcut, reviewed sample counts and existence of account credential files. It makes no Gmail/Notion API requests, sends no email, creates no notes, records no microphone audio and trains no model. It saves a private report in logs/mvp_readiness.json. An installed speech engine is not proof of audible output; configured startup is not proof of a successful sign-in run.

## Voice flow on this PC

Quit the old Bilal instance from the tray and restart main.py. Keep speaker volume comfortable. Test these at normal distance, then farther away and with ordinary background noise:

1. Say ?Hey Bilal, explain the difference between a website and a web app.? Expect the small companion to appear, hear the complete reply, then see it hide. Note any clipped first words or missing activation.
2. Say ?Hey Bilal, draft an email. Subject: Meeting update. Body: Our meeting is tomorrow?? Pause three seconds, then continue ??at 3 PM.? Expect all words in the transcript and a popup asking for the missing recipient. Do not paste a real address or send until account testing is authorized and configured.
3. Enter an incomplete address, such as a name only. Expect local validation and no draft. Cancel the popup. Expect the task to stop without an email action.
4. While Bilal is processing a harmless question, say ?never mind.? Expect cancellation and no later action. The offline interruption recognizer is English; cancellation after an already completed action cannot undo it.
5. Turn the network off temporarily and ask a harmless question. Expect a spoken failure, no success claim, and hiding after speech finishes. Restore the network yourself before further tests.
6. Sign out and back in when convenient. Expect one tray instance, a hidden companion before wake, and successful activation. A reboot is not required for testing sign-in startup.

Record actual pass/fail and the transcript if a step fails. The automated GUI tests simulate audio, speech and Gmail effects; they do not prove microphone recognition, speaker audibility or account delivery.

## Collect reviewed wake data

Use the tray's Collect reviewed wake examples action. The app pauses wake monitoring so it does not share the microphone with collection. Collect two separate sessions, preferably with different distance/noise. Each requests ten full ?Hey Bilal? examples and ten negatives. Negatives should include ?hey? alone, ?hee haa?, confusable phrases and ordinary conversation. Each clip is played locally before you confirm its label; reject mistakes. No clips go to transcription services during collection.

Minimum training preparation requires ten valid reviewed clips per class and two sessions containing both classes. Missing/changed clips are excluded by their saved hashes. Evaluation uses the deployed threshold and consecutive-frame policy. Passing the dataset count gate does not establish good recognition.

```powershell
.\venv\Scripts\python.exe .\evaluate_wake_learning.py
.\venv\Scripts\python.exe .\train_reviewed_wake.py --train-candidate
```

Training outputs a separate candidate. Collect independent microphone evaluation samples after training before considering promotion. Keep the baseline deployed until acceptance demonstrates improvement without increased false triggers. This work has not changed its threshold or trained/promoted a new model.

## Gmail and Notion ? live tests pending

The standalone app has no account connections on this PC. Live access tests require explicit authorization and account setup. Codex's account connections do not supply Bilal's credentials.

Gmail setup needs your Desktop OAuth client JSON; complete consent locally. Notion setup accepts the integration token through a hidden local prompt. Never paste tokens in chat. Refer to MVP_IMPLEMENTATION.md for the setup commands.

After authorization/setup, first create and reject a test draft addressed to your own chosen email address. Check that no message appeared in Sent. Then create a fresh test draft, inspect exact recipient/subject/body, approve in Bilal's review window, and verify receipt. Pasting an address is not sending approval. A changed draft must require a new review. Never automatically retry an uncertain send; inspect Gmail Sent.

For Notion, choose and share a real test parent page. Start with read-only page discovery and reading. Then deliberately request a test note, compare its title/body with readback, and inspect the created page. Do not create a page as an unsolicited connectivity probe.

## Background playback regression

After offline model setup and restarting Bilal, play ordinary YouTube speech/music for several minutes without saying the wake phrase. Expect the companion to remain hidden and no new agent action. Then say “Hey Bilal, explain websites” with the video playing at normal volume; check activation and that the first command words are retained. Repeat with “hey” alone and non-trigger chatter; expect no activation. Finally turn wake listening off from the tray and repeat the full phrase; expect no activation. The test is not a guarantee of speaker isolation: media that actually contains the complete trigger can still activate this version.
