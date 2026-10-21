# MVP implementation and acceptance status

Updated 2026-10-11, Asia/Karachi. See MVP_BASELINE.md for the pre-change findings.

| Area | Implemented | Validation and remaining work |
|---|---|---|
| Wake | Continuous wake-to-command microphone stream, detector re-priming, local activation examples, correct/false feedback, reviewed collection, separate candidate-training workflow | 36 historical replay variants exposed weak noise/quiet robustness. They are not fresh field samples. No deployed model or threshold was changed. Fresh balanced sessions are required. |
| Pauses/cancel | Four-second pause grace, 90-second limit, bare-wake handling, local never-mind control, offline English cancellation while processing, click-to-interrupt speech | Pause/stream/cancellation tests pass. Generated “never mind” was recognized offline at 0.934 confidence. Live accent, distance and music cancellation tests remain necessary. In-flight network work may take time to return; cancellation prevents subsequent actions and cannot undo completed effects. |
| Learning | SQLite preferences/aliases/pronunciation/procedure notes, explicit confirmation, persistence, vocabulary hints and model context | Real Gemini called propose_memory and left it unconfirmed. Persistence and rejection checks pass. Detection clips are unlabelled until user feedback. No silent training/promotion. |
| Execution | Public webpage reading with continuation/source URLs, arbitrary HTTP(S) Chrome opening, accessible link URLs, current-goal grounding, stale-ID invalidation, uncertain-write mutation blocking | Live official Python documentation read succeeded. Accessible Windows controls remain required; no general screenshot vision or full browser DOM driver. Universal app compatibility is not claimed. |
| Business | Gmail plain-text draft/readback/review/send/receipt; recipient/content-bound one-shot approvals; Notion page search/read/private note creation/readback | Fixture tests cover draft changes, duplicate approval, payload tampering, timeout/crash recovery, pagination and note verification. Live Gmail/Notion tests are pending by user choice. No real email or Notion page was sent/created during this work. |
| Reliability | Startup, silent workers, shutdown/painter cleanup, cancellation, encryption, privacy filtering and failure tests | 123 automated tests pass. Tests are selected behavior checks, not universal reliability evidence. Reboot/sign-in and fresh physical voice acceptance still require field testing. |

## Use the new features

Quit the running old version from the tray and restart Bilal. Dependencies are installed on this PC; other installs should run pip install -r requirements.txt.

Say “never mind” or “cancel that” as a new utterance while processing. These phrases use Windows' offline en-US recognizer. Cancellation while recording is handled once the utterance is transcribed. Click the tiny companion to interrupt spoken output and start a new request.

Ask Bilal to remember a preference or correction. The review window must be approved before it is stored. Memory keys can use preferred_city, language, alias.<name>, pronunciation.<word>, or procedure.<name>. Credentials are not valid memory. Confirmed preferences and vocabulary hints are shared with the reasoning/transcription providers when used.

The tray offers Pending approvals, Last wake was correct, Last wake was a false trigger, and Collect reviewed wake examples. Ordinary tasks do not resurrect old unrelated approvals. Waiting approvals remain visible until a decision and persist across restart. Interrupted executing actions become uncertain and are never automatically replayed.

## Wake acceptance and training

Use the tray collection action twice, preferably in separate sessions/distance/noise conditions. Each session prompts for positives and confusable/ordinary negatives, including “hey” alone. Confirm each label honestly. This is local capture, not cloud transcription.

Equivalent command:

```powershell
.\venv\Scripts\python.exe .\collect_wake_examples.py --label both --count 10
.\venv\Scripts\python.exe .\evaluate_wake_learning.py
.\venv\Scripts\python.exe .\train_reviewed_wake.py --train-candidate
```

Training requires at least ten reviewed examples per class and at least two balanced source sessions. It uses session-held-out diagnostics and retains baseline/generic negative data. Outputs go to models/candidates/, never the deployed model directory. Fresh independent microphone tests are required before deployment. Current reviewed dataset is empty; no new candidate was trained.

## Account setup — deferred

Bilal's standalone app needs its own authorization, separate from Codex's connectors. Tokens are encrypted with Windows DPAPI for the current Windows user in .secrets/. Do not paste credentials into chat or commit them.

Gmail: enable Gmail API in your Google project, create a Desktop OAuth client, obtain its client JSON, then deliberately run:

```powershell
.\venv\Scripts\python.exe .\setup_connections.py gmail --client-json "C:\path\to\desktop-client.json"
```

Complete the Google consent yourself. The app requests draft/send and account identity access. The Gemini API key is not Gmail authorization. Plain-text drafts are supported; attachment sending is not connected. Review shows the account, recipients, subject and body. Sending uses the reviewed raw content and checks a Sent receipt. A send timeout may already have reached Gmail: inspect Sent before any explicit retry.

Notion: create an integration with the required page permissions and share the Bilal AI page with it. Then run:

```powershell
.\venv\Scripts\python.exe .\setup_connections.py notion
```

Enter the token at the hidden local prompt. Select a real parent page from notion_search before creating a note.

References: [Gmail drafts](https://developers.google.com/workspace/gmail/api/guides/drafts), [Google desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app), [Notion search](https://developers.notion.com/reference/post-search).

## Data boundaries

Private memory, approvals and wake recordings are in data/. Encrypted account credentials are in .secrets/. Runtime traces and replay diagnostics are in logs/. All are excluded from Git. Only explicitly reviewed wake labels are eligible for candidate preparation. Raw private microphone clips were not uploaded during the regression/stress tests.

The agent cannot approve its own action: no approve/send model tool exists, and its desktop worker excludes its parent and Bilal approval windows. The user interface is the approval boundary. Web/Notion content remains untrusted context and cannot grant permission.

## Missing-detail popup

The model-selected request_input tool pauses a task for a typed/pasted detail. A 360-pixel-wide popup validates a single email address, submits once, and closes on submission/cancel. The current request and prior tool progress are retained so follow-up can use the already dictated body. No other mutations in that model response are executed once clarification is requested. Human email sending approval remains separate. A live Gemini test requested the missing address and retained the original email body after submission against a simulated connector; no live account write occurred.

## Integrated acceptance follow-up

Six GUI/controller integration checks now cover simulated wake-to-command handoff, recording/transcription/reply, retaining the companion during speech, automatic hiding, missing recipient to reviewed fixture send, input cancellation and audible failure without stale success. Errors and empty captures are now spoken when Speak replies is enabled. Wake collection plays clips before review; changed/missing audio is excluded by hash, and evaluation requires balanced sessions using current detection settings. See FIELD_ACCEPTANCE.md and check_mvp_readiness.py for remaining physical/account checks. No fresh user clips, candidate training or live account writes occurred in this follow-up.

## Confirmed laptop power actions

Sleep, shutdown and restart now have model-requested, action-bound human confirmation. The local executor accepts only three fixed actions. Confirmation expires after 120 seconds; rejecting/cancelling, altered approval payloads and duplicate approval cannot execute it. Power effects are blocked in generic desktop controls/shortcuts. Shutdown/restart preserve save-work handling, and sleep retains Windows wake events. Gemini correctly requested confirmation for all three phrases in live model tests; power execution and GUI tests used mocked Windows calls. No actual sleep/shutdown/restart was performed, and Windows may deny or block a request.

## Full-phrase wake gate — 2026-10-21

The most recent task log contained only “Uh.”, confirming that classifier acceptance alone could reach the agent. Activation now requires offline full-phrase verification before the popup and command capture. Wake audio is retained during the check; automatic command transcripts without the trigger are discarded. Disabled wake, stale/unverified wake events, verifier errors, ordinary high-score background audio and late results after pausing cannot start automatic capture in regression checks. Manual requests remain unaffected. The local verifier adds a separate public pretrained speech model; the deployed wake classifier and threshold are unchanged. Actual playback of the trigger remains a limitation without speaker identification/echo cancellation.

The verifier uses an explicit wake-phrase vocabulary context and a strict acoustic recognition score, rather than accepting the hinted text alone. In diagnostic replay it accepted 9/10 historical positive-labelled clips (the rejected label was the user-reported “hey Bill”), rejected 13 historical negatives and 9 generated speech negatives, and retained all 3 hits produced by the unchanged classifier on those historical clips. These are calibration diagnostics, not a general accuracy claim or fresh YouTube acceptance. Fixed decoder context can bias recognition, so the classifier, local full-phrase/score gate and final command-transcript guard all remain required. Verification generally adds about two seconds on this PC; command audio is buffered during that time.
