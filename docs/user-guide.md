# User guide

[Documentation](README.md) · [Project overview](../README.md) · [Feature reference](features.md) · [Field acceptance](FIELD_ACCEPTANCE.md)

Bilal is an experimental Windows agent with background tasks and local tools. Hold **left Ctrl + left Shift**, speak, and release to submit. You can inspect work, saved answers and approvals from **Tasks, history and settings** in the tray.

**This build does not complete the full 138-capability target.** Check [current implementation/acceptance status](CAPABILITY_STATUS.md) and the [target spec](CAPABILITY_SPEC.md). Wake defaults off until independent acceptance passes. Gmail/Notion live account tests remain pending by choice; external-agent writing is not available.

The interface, assistant replies, spoken responses, and clarification prompts use **English**, including when you speak another language. Names, addresses, and dictated document/email content are preserved; explicitly requested non-English document content is separate from the interface language.

## 1. Start and stop

Complete the [README quick start](../README.md#quick-start), including API keys and dependencies. The offline model is optional preparation for gated wake activation, not required for hold-to-talk. From the project folder in PowerShell:

```powershell
.\venv\Scripts\python.exe .\main.py
```

Bilal starts hidden. Find its icon in the Windows system tray, including the hidden-icons area. The character appears after verified activation or manual interaction. Before running updated code, choose **Quit Bilal** on the existing instance; a second launch does not replace the running copy.

To exit completely, use **Quit Bilal**. Hiding/closing the companion leaves the assistant running. Ctrl+C also requests shutdown when launched through a terminal; the tray is the normal everyday exit.

## 2. Give a spoken request

Hold **left Ctrl + left Shift**, wait for listening, say “Explain the difference between a website and a web app,” then release. No wake phrase is needed. The companion hides on release while the request is transcribed and queued; spoken output can continue in the background. You can give more work while queued tasks run.

Automatic full-command follow-up capture is off. Start each turn explicitly. General clarification can be answered using the same held shortcut; an email-address question opens a paste box. A new hold capture allows thinking pauses without silence stopping it, but has a 600-second chunk bound. Ordinary manual/wake capture still has four-second silence and 90-second limits.

### Optional wake activation

“Hey Bilal” is unavailable by default until an independent report records at least 50 positive trials, at least 90% true activation, one hour of negatives, fewer than one false activation per hour, and a timestamp no older than 30 days. The local verifier model is also required. Neither model installation nor training examples satisfy acceptance. See [testing](testing.md).

After accepted activation is enabled, use the full “Hey Bilal” phrase with your request. Audio is buffered during verification. “Hey” alone is not a trigger; media actually saying the full phrase can still activate it because this is not voice identity recognition.

## 3. Hold to talk, record manually, or type

Hold **left Ctrl + left Shift** from another app or the desktop, wait for the listening state, and speak. Release any key in the chord to submit and hide the companion immediately. Processing and the spoken answer can continue in the background; release does not cancel the task. While held, a new hold capture does not stop for a thinking pause or an initial no-speech timeout. It has a 600-second chunk bound; processing that chunk can begin before release, while the companion stays visible. This is a bound, not unlimited dictation. The global hook tracks configured shortcut keys, forwards keystrokes, ignores injected keys and does not log typed text. Other apps can still react to the shortcut. Change it or choose toggle mode in Task Center Settings, then restart. Left Ctrl + left Shift alone is an opt-in setting.

The shortcut never approves an action or submits an email-address dialog. It can record an answer to a spoken general clarification while preserving the pending task. Holding during spoken output interrupts speech before a new capture can start; it is not simultaneous recording of Bilal’s own reply. If work is already processing, the hold does not cancel its completed actions or guarantee a second immediate recording.

If automatic activation is unavailable:

1. Open the tray menu and choose **Start / finish recording**.
2. Speak after recording is ready. Manual recording does not require the wake phrase.
3. Choose the same action to finish early, or let silence finish capture.

For typed input, choose **Read reply / type a request**, enter the request, and send. This bypasses microphone recognition and helps distinguish a transcription problem from task execution.

Double-click the avatar for Quick Input. Click an idle visible companion to start recording; clicks during processing or speech are ignored. Use the tray recording control or hold-key release to finish capture; drag to reposition it; right-click for controls. Space controls recording when the companion has focus and the request input does not. The separate left Ctrl + left Shift shortcut is global; Space remains a focused-window control.

## 4. Read the character states

| State | Meaning |
| --- | --- |
| Hidden | Waiting in the background, or wake activation is disabled |
| Idle | Ready or presenting an ordinary reply |
| Listening | Recording your command |
| Loading | Preparing audio or transcribing |
| Processing | Reasoning or using tools |
| Speaking | Reading the reply aloud |
| Success | Tool verification supported completion |
| Error | The request needs attention or could not finish |
| Inactive | Wake listening is disabled or pending work is stopping |

Automatic full-command follow-up capture is off by default. The listening state should therefore represent an explicitly started recording. A busy or speaking avatar ignores clicks; it should not open another microphone capture.

Hidden does not mean the process is off. Check **Listen for Hey Bilal (acceptance required)** in the tray for the activation setting. The conversation view has more detail than the small character shows.

## 5. Try available tasks

These examples can be spoken while holding the shortcut or typed. They are natural requests, not required sentences:

| Goal | Example | Check the actual outcome |
| --- | --- | --- |
| Question | “explain a web app in simple terms.” | The answer addresses the question |
| Open an app | “open Notion.” | The intended installed app opens |
| Music | “play Blinding Lights by The Weeknd on Spotify.” | Playback starts with the right track/artist |
| Search | “search YouTube for startup bookkeeping.” | Chrome opens the intended search |
| Public page | “read this public webpage and summarize it,” followed by its URL | The answer uses readable content and its source |
| Memory | “remember my preferred city is Karachi.” | Review the proposed memory before confirming |
| Email | “draft an email saying our meeting is tomorrow at 3 PM.” | Missing details are requested; sending waits for review |
| Notion | “find my Bilal AI page.” | The page is shared with Bilal's integration |
| Power | “put my laptop to sleep.” | The review shows sleep and waits for your decision |

Opening an app is only the first step of a larger task. Some apps expose too little accessible information for further work. Search results are not proof of music playback or completed research.

Include an artist for music when possible. Bilal can interpret likely title mistakes from context, but correct it if it chooses the wrong track. For changing information, include city/date and ask for a current lookup. Bilal uses quiet search and readable source text rather than opening tabs unless you explicitly ask. Blocked sources should produce a short blocker, not repeated searches. For prayer times, give city, country, and date; Bilal returns calculated prayer starts and the method, not a mosque congregation schedule. It does not infer your location through GPS/IP.

## 6. Supply missing details

You can dictate content before providing every field:

1. Say: “draft an email. Subject: Meeting update. Body: Our meeting is tomorrow at 3 PM.”
2. If the recipient is missing, Bilal asks for an address and opens a small input box.
3. Paste one complete email address and press **Enter** or **Continue**.
4. Bilal continues using the content already given.
5. Review the actual draft before approving or rejecting sending.

For a general question such as “Which city and country?”, no text dialog appears: hold left Ctrl + left Shift, say the answer, and release, or, after wake acceptance, say “Hey Bilal” followed by the answer. Bilal resumes the original task rather than treating the city as an unrelated request.

Invalid email input stays visible with a validation message. Correct it or cancel. Supported text fields accept up to 2,000 characters. Use this box for requested details, not passwords or API keys.

**Pasting an address is not sending approval.** Cancelling stops the pending continuation. Tasks persist, but pending dialog/literal context is not fully recoverable. After restart, inspect the blocked/interrupted task and provide a fresh request rather than blindly replaying earlier effects.

## 7. Review approvals

Email sending, saving a proposed memory, and power actions have dedicated review windows. Read the actual action/content, then approve or reject. The agent cannot approve for you.

For email, inspect recipient, subject, and body. Approval applies once to the reviewed draft. Changes require a fresh review. Rejecting can leave an unsent draft in Gmail. If sending is uncertain, inspect Gmail Sent before retrying.

For power, check **sleep**, **shutdown**, or **restart** carefully. Confirmation expires after two minutes. Save work before deliberately confirming a real power test. Windows can block/delay the transition, and an asleep PC cannot hear Bilal.

**Pending approvals** in the tray opens waiting items. Approval records can persist across restarts; expired or changed actions cannot use an old confirmation. Requested Notion note creation is a write but does not use Gmail's send review.

## 8. Cancel or interrupt

When the optional offline cancellation listener is enabled, try **“never mind,” “cancel that,”** or **“stop Bilal”** during processing. It is not guaranteed to be available when production wake is off; use the global stop shortcut for a manual fallback. The offline English interruption recognizer has a small phrase list; noise, accent, and microphone conditions can affect it.

For current-request cancellation, choose **Cancel request** in the tray. To stop all background work, speech/capture and the screen session, press **left Ctrl + left Alt + Backspace**, or choose **Stop all background tasks**. Stopping is cooperative and in-flight effects may still complete. Escape cancels an active request when Bilal has focus; when idle it hides the companion. Escape is not monitored globally.

Cancellation stops pending work/speech where possible. It cannot undo completed actions such as opening an app, creating a note, or sending an approved message. Cancelling an active review rejects that reviewed action. For an account operation already in flight, inspect the service before repeating.

## 9. Tray controls

| Item | Purpose |
| --- | --- |
| Show Bilal | Bring the companion above the taskbar |
| Start / finish recording | Start capture or finish early |
| Cancel request | Stop pending work |
| Read reply / type a request | Open conversation and typed input |
| Listen for Hey Bilal (acceptance required) | Enable wake only after independent acceptance |
| Tasks, history and settings | Task states, saved artifacts, policy approvals, audit and Settings |
| Paste exact text / quick input | Open the exact-payload panel |
| Ask about a window / point to ask | Explicit one-shot screen sharing choice |
| Stop all background tasks | Cancel pending task work; completed effects remain |
| Speak replies | Toggle speech output |
| Collect reviewed wake examples | Start guided local recording/label review |
| Pending approvals | Review waiting actions |
| Last wake was correct | Label the available latest wake sample positive |
| Last wake was a false trigger | Label the available latest wake sample negative |
| Clear conversation | Clear the conversation while idle |
| Quit Bilal | Stop the assistant completely |

Clear conversation does not erase recordings, credentials, or approved memory. These are separate stores. Settings such as allowed folders/domains and talk-shortcut configuration persist. Changing the shortcut requires restart. Do not assume a dragged companion position persists.

## 10. Connect Gmail and Notion

Connections belong to standalone Bilal; Codex access does not transfer automatically. Follow the account connection instructions in [Getting started](getting-started.md).

Gmail needs a Desktop OAuth client JSON and local consent. Notion needs an integration token entered at the hidden setup prompt and sharing of intended pages. Do not paste credentials in chat or the contextual input box.

Live acceptance remains pending. After setup, follow [field acceptance](FIELD_ACCEPTANCE.md), beginning with read-only checks and deliberately selected test content. A credential file existing does not establish a working connection.

## 11. Start after Windows sign-in

From the installed project folder:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py
```

This installs/updates the current user's shortcut. At the next sign-in, Bilal launches without a terminal and stays hidden. It is not a pre-login service. Keep the project and virtual environment in place, or update the shortcut after moving them.

Disable automatic startup:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py --remove
```

To verify, quit Bilal and sign out/in when convenient. Look for one tray instance, then test the trigger. Finding a shortcut in a readiness report does not prove the real sign-in launch worked.

## 12. Improve recognition deliberately

Use **Last wake was correct** or **Last wake was a false trigger** to label the latest available sample. Labels do not immediately deploy a new model.

For a fuller dataset:

1. Choose **Collect reviewed wake examples** while idle.
2. Follow the console; wake monitoring pauses to release the microphone.
3. Record the full phrase as positives. Use “hey” alone, “hee haa,” ordinary speech, and confusable sounds as negatives.
4. Listen to each playback and accept only correct labels.
5. Collect another balanced session with different distance/noise.

Each session requests ten positives and ten negatives. Preparation needs ten valid reviewed clips per class and two balanced sessions. Follow the [reviewed wake learning workflow](testing.md#reviewed-wake-learning-workflow) to evaluate/train a separate candidate; [voice calibration](../training/VOICE_CALIBRATION.md) is an additional specialist reference. Fresh independent evaluation must precede deliberate promotion. This is not continuous training, and “hey” alone should not become a trigger.

## 13. Common problems

| Symptom | First action | Relevant limitation |
| --- | --- | --- |
| No wake popup | Use default hold-to-talk; inspect acceptance status | Wake is gated off without fresh independent evidence |
| Video activates it | Check whether it said the full trigger; label false samples | No speaker identity or echo cancellation |
| Capture stops during thought | Keep pauses below four seconds or continue in another request | Silence-based endpoint detection |
| Wrong transcript | Type the intended request to compare; clarify names | Speech recognition is imperfect |
| Correct words, wrong action | Report exact request, reply, and observed action | Reasoning/tool choice can fail separately from audio |
| App opens, task stops | Check actual controls and returned error | Accessibility coverage varies |
| Spotify searches without playing | Check playback/error rather than accepting search as success | Media session/account/app conditions matter |
| Silent replies | Enable Speak replies; check volume/output/installed voice | Available engine does not establish audible output |
| Question/transcription fails | Check network and provider configuration/quota | Full assistance is not offline |
| Gmail/Notion unavailable | Configure Bilal's connection and page sharing | Codex access is separate |
| Input box stays open | Correct validation or cancel | Email needs one complete address |
| Uncertain account outcome | Inspect the service before retrying | A timed-out write may have completed |
| Updated code seems ignored | Quit the old instance and restart | Only one GUI instance runs |

A useful report includes exact request, approximate time, transcript, expected/actual result, and error. Avoid sharing secrets or private account content. Recorded audio/transcripts normally share `recordings/command_<id>` as `.wav` and `.txt`. Production replies and tool results are saved in Task Center history/steps. Older synchronous runs can also have `.answer.txt` replies and legacy trace logs. Readiness reports live in ignored `logs/`; all these stores can contain private content.

## 14. Local readiness check

For local configuration checks and automated regressions without microphone recording or live account actions:

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py --tests
```

The private report is `logs/mvp_readiness.json`. It does not establish physical recognition, audible speakers, actual email delivery, real power transitions, or successful sign-in startup. Complete [field acceptance](FIELD_ACCEPTANCE.md) for those checks.


## 15. Tasks, saved answers, and status

Open **Tasks, history and settings** from the tray:

- **Tasks:** select work to read its goal, owner, state, recorded steps, result and error. Pause, Resume or Cancel affects the selected task; Stop all affects active tasks.
- **History:** search saved answers, drafts and agent output; select an artifact to read it.
- **Approvals:** inspect precise tool actions waiting for review.
- **Audit:** inspect recorded task/policy events.
- **Settings:** choose allowed folders, browser domains, shortcut/toggle mode, provider keys, sensitive-window terms and dry run.

Three workers run by default. A planner can split a multi-command request into child tasks; dependencies wait for earlier work to finish. A parent saying children were queued does not mean those children completed. Live multi-command accuracy is still acceptance-pending.

Ask “What are you doing?”, “What's pending?” or “Did Codex finish?” for stored status. You can also say “pause task”/“cancel task”/“resume task” with a task ID or distinguishing goal. If several tasks are similar, use the visible ID rather than a vague name.

After a restart, unfinished work is marked interrupted rather than silently replayed. A task with possible writes/recorded effects may refuse Resume and require inspection/new review. Memory-only pasted payloads and screen frames expire. Pausing acts at a tool boundary and may not stop an in-flight call immediately.

Schedules are in-app tasks, not Windows wake timers. Ask for an explicit time and timezone and review creation. Bilal must be running and the laptop awake for them to run. The current weekday filter uses Pakistan time. Do not depend on this foundation for an unattended critical deadline without acceptance testing.

## 16. Paste exact text without rewriting it

1. Show Bilal from the tray, then double-click the avatar, or choose **Paste exact text / quick input**.
2. Put the exact payload in the upper text area and give it a useful label, such as “recipient email” or “config value.”
3. Choose **Add exact text**, or leave the current payload present when sending.
4. Type a separate instruction below, or hold the talk shortcut while the panel stays open and explain what to do with that snippet.
5. Choose **Send instruction** for typed work, then review any resulting action.

The planner gets a reference, label and size; the local executor substitutes the original string. Keep names, addresses, URLs, config text and code in the payload area when character-for-character preservation matters. Limit: 2 MB per payload. Preservation in Bilal is not proof of insertion into every target app; inspect the destination.

**Secret — memory only, never saved in history** marks a secret payload. Some token/card patterns are detected automatically, but detection is incomplete. Provider credentials belong in Settings, not the instruction. Secret connector/cloud transport is not generally enabled by this feature.

Added non-secret snippets can be saved locally. **Clear local snippets** or closing the panel clears its vault; already queued tasks retain their copies until finishing. Restart loses memory-only copies and affected tasks need fresh input. Do not treat this as an encrypted password manager.

## 17. Allow folders and review file effects

In **Settings**, choose **Allow a folder…** and select only a project/test folder Bilal needs. Allowed folders start empty. Removing one removes future tool access; it does not undo earlier changes. Private/system/credential paths remain restricted even inside a chosen root.

You can request text/document reading or search, copy/move files, write exact text, recycle an individual file, or restore a saved version. Writes, moves, recycling and restores wait in Task Center **Approvals**. A new copy is a lower-risk action and does not require the same write review.

Read the exact target path and content. Secret content is hidden until **Reveal exact payload locally**. Choose **Approve this exact action** or **Reject**. New policy approvals expire after ten minutes; a high-risk action may require typing `CONFIRM`. A single-step approval resumes that step only. A deterministic plan can batch up to 20 file/contact/project/schedule calls in one review; editing it invalidates the old approval. The plan stops at its first failed check and never replays earlier writes. Dynamic UI batches and external-agent write execution are excluded.

Overwrites preserve version snapshots and verify resulting bytes. Snapshots on Windows are encrypted for your Windows user, so keep that account available. Recycling does not support directories. Versions do not undo email sends, account notes, or arbitrary app actions.

For inspection without the tool effects, enable **Dry run: show planned tool calls without executing** in Settings. Review the recorded plan, then disable it before deliberately executing real work. Dry run is not proof an action would succeed.

## 18. Use Bilal's owned Chrome session

Add exact hostnames through **Settings → Set allowed browser domains**. Use `example.com`, not a wildcard or a full URL. `www.example.com` is a different hostname. Resources/redirects on unallowed hosts can be blocked; add only domains needed for the intended task.

Owned browser tools open Chrome in Bilal's separate profile. They do not control or borrow sign-in cookies from personal Chrome tabs. Bilal can list owned tabs, read observed text/elements, fill supported fields and check their value, and click supported observed controls. It must read again after elements change.

Login/password, file upload/download, submission, publishing, purchase and destructive controls are blocked. This path is not full browser automation. The older explicit search/opening tools can still open Chrome searches; a visible personal tab is not automatically an owned DOM tab.

## 19. Ask about a screen or point

Choose **Ask about a window / point to ask** in the tray, or ask a screen question and wait for its capture choice. Select one window, one monitor, all monitors, or point/drag a region. A visible sharing indicator appears before the chosen image goes to Gemini.

The image remains in memory; its answer can persist in task history. This is a question-only model with no action tools. The daily limit is 20 screen questions. A sensitive-window title/process guard can reject overlapping views. It is not automatic pixel redaction: inspect what you choose to share.

Pointer mode intends to intercept the click/drag rather than click the underlying app. Secure-desktop, exclusive-fullscreen, and mixed-DPI cases remain physically unaccepted; this phase is partial. Escape closes the overlay, and global stop-all ends screen interaction. A lost frame needs fresh explicit sharing.

## 20. Delegate analysis to Codex or Claude

Ask for an analysis/plan and optionally refer to a saved artifact, for example “Ask Codex to analyze the saved summary.” The adapter runs without action tools, captures its answer, and saves a task artifact. Read its actual output in History; it has not edited your project.

A local read-only Codex live check passed. Official Claude Code CLI **2.1.309** is installed locally, but it needs **Settings → Set a provider API key in Windows Credential Manager → ANTHROPIC_API_KEY** before bare-mode use. No live Claude key test has passed. Subscription login is not a substitute for this adapter's key.

Neither external agent has write access, a complete resumable session workflow, or proven project-only OS read isolation. A read-only sandbox is not a guarantee that other files on the machine are invisible. Do not delegate private artifacts or expect a plan to be automatically executed.
