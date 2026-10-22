# User guide

[Documentation](README.md) · [Project overview](../README.md) · [Feature reference](features.md) · [Field acceptance](FIELD_ACCEPTANCE.md)

Bilal is an experimental Windows voice agent. Ordinary use is hands-free: say **“Hey Bilal”**, give the request, and listen to the answer. You can also hold **left Ctrl + left Shift** globally to speak and release either key to submit. It can act through its implemented tools and the interfaces available on your PC. Gmail and Notion need separate setup; their live acceptance tests remain pending.

The interface, assistant replies, spoken responses, and clarification prompts use **English**, including when you speak another language. Names, addresses, and dictated document/email content are preserved; explicitly requested non-English document content is separate from the interface language.

## 1. Start and stop

Complete the [README quick start](../README.md#quick-start), including API keys, dependencies, and the offline wake model. From the project folder in PowerShell:

```powershell
.\venv\Scripts\python.exe .\main.py
```

Bilal starts hidden. Find its icon in the Windows system tray, including the hidden-icons area. The character appears after verified activation or manual interaction. Before running updated code, choose **Quit Bilal** on the existing instance; a second launch does not replace the running copy.

To exit completely, use **Quit Bilal**. Hiding/closing the companion leaves the assistant running. Ctrl+C also requests shutdown when launched through a terminal; the tray is the normal everyday exit.

## 2. Speak naturally

Say a complete request:

> Hey Bilal, explain the difference between a website and a web app.

The trigger and request can be one utterance. Wake verification buffers incoming audio, so a short delay before the character appears is possible. Avoid immediately repeating several times; the first request may still be verifying.

Continue while the character listens. **Four seconds of detected silence can end recording**, so longer thinking pauses can split a request. Ordinary wake/manual capture lasts up to 90 seconds and stops after the initial wait if no speech is detected. These limits are not a fixed delay for every reply.

Bilal transcribes the recording, reasons, performs available steps, and speaks the result when **Speak replies** is enabled. The companion hides when the request and reply finish. Automatic follow-up listening is disabled by default. Use the wake phrase or hold-to-talk for another turn. A missing email-address or approval dialog stays visible until you respond.

Only the full **“Hey Bilal”** phrase should activate it automatically. “Hey” alone is unsupported. A video actually saying the full phrase can still trigger this version: it does not identify your voice.

## 3. Hold to talk, record manually, or type

Hold **left Ctrl + left Shift** from another app or the desktop, wait for the listening state, and speak. Release either key to submit and hide the companion immediately. Processing and the spoken answer can continue in the background; release does not cancel the task. While held, a new hold capture does not stop for a thinking pause or an initial no-speech timeout. It has a 600-second chunk bound; processing that chunk can begin before release, while the companion stays visible. This is a bound, not unlimited dictation. The shortcut polls only modifier states and records no typed keys. Other apps still receive the modifiers, so their shortcuts may also react.

The shortcut never approves an action or submits an email-address dialog. It can record an answer to a spoken general clarification while preserving the pending task. Holding during spoken output interrupts speech before a new capture can start; it is not simultaneous recording of Bilal’s own reply. If work is already processing, the hold does not cancel its completed actions or guarantee a second immediate recording.

If automatic activation is unavailable:

1. Open the tray menu and choose **Start / finish recording**.
2. Speak after recording is ready. Manual recording does not require the wake phrase.
3. Choose the same action to finish early, or let silence finish capture.

For typed input, choose **Read reply / type a request**, enter the request, and send. This bypasses microphone recognition and helps distinguish a transcription problem from task execution.

Click an idle visible companion to start recording; clicks during processing or speech are ignored. Use the tray recording control or hold-key release to finish capture; drag to reposition it; right-click for controls. Space controls recording when the companion has focus and the request input does not. The separate left Ctrl + left Shift shortcut is global; Space remains a focused-window control.

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

Hidden does not mean the process is off. Check **Listen for Hey Bilal** in the tray for the activation setting. The conversation view has more detail than the small character shows.

## 5. Try available tasks

These examples are natural requests, not required sentences:

| Goal | Example | Check the actual outcome |
| --- | --- | --- |
| Question | “Hey Bilal, explain a web app in simple terms.” | The answer addresses the question |
| Open an app | “Hey Bilal, open Notion.” | The intended installed app opens |
| Music | “Hey Bilal, play Blinding Lights by The Weeknd on Spotify.” | Playback starts with the right track/artist |
| Search | “Hey Bilal, search YouTube for startup bookkeeping.” | Chrome opens the intended search |
| Public page | “Hey Bilal, read this public webpage and summarize it,” followed by its URL | The answer uses readable content and its source |
| Memory | “Hey Bilal, remember my preferred city is Karachi.” | Review the proposed memory before confirming |
| Email | “Hey Bilal, draft an email saying our meeting is tomorrow at 3 PM.” | Missing details are requested; sending waits for review |
| Notion | “Hey Bilal, find my Bilal AI page.” | The page is shared with Bilal's integration |
| Power | “Hey Bilal, put my laptop to sleep.” | The review shows sleep and waits for your decision |

Opening an app is only the first step of a larger task. Some apps expose too little accessible information for further work. Search results are not proof of music playback or completed research.

Include an artist for music when possible. Bilal can interpret likely title mistakes from context, but correct it if it chooses the wrong track. For changing information, include city/date and ask for a current lookup. Bilal uses quiet search and readable source text rather than opening tabs unless you explicitly ask. Blocked sources should produce a short blocker, not repeated searches. For prayer times, give city, country, and date; Bilal returns calculated prayer starts and the method, not a mosque congregation schedule. It does not infer your location through GPS/IP.

## 6. Supply missing details

You can dictate content before providing every field:

1. Say: “Hey Bilal, draft an email. Subject: Meeting update. Body: Our meeting is tomorrow at 3 PM.”
2. If the recipient is missing, Bilal asks for an address and opens a small input box.
3. Paste one complete email address and press **Enter** or **Continue**.
4. Bilal continues using the content already given.
5. Review the actual draft before approving or rejecting sending.

For a general question such as “Which city and country?”, no text dialog appears: hold left Ctrl + left Shift, say the answer, and release, or say “Hey Bilal” followed by the answer. Bilal resumes the original task rather than treating the city as an unrelated request.

Invalid email input stays visible with a validation message. Correct it or cancel. Supported text fields accept up to 2,000 characters. Use this box for requested details, not passwords or API keys.

**Pasting an address is not sending approval.** Cancelling stops the pending continuation. After a restart, restate a request that was waiting for clarification; this input flow is not a durable task queue.

## 7. Review approvals

Email sending, saving a proposed memory, and power actions have dedicated review windows. Read the actual action/content, then approve or reject. The agent cannot approve for you.

For email, inspect recipient, subject, and body. Approval applies once to the reviewed draft. Changes require a fresh review. Rejecting can leave an unsent draft in Gmail. If sending is uncertain, inspect Gmail Sent before retrying.

For power, check **sleep**, **shutdown**, or **restart** carefully. Confirmation expires after two minutes. Save work before deliberately confirming a real power test. Windows can block/delay the transition, and an asleep PC cannot hear Bilal.

**Pending approvals** in the tray opens waiting items. Approval records can persist across restarts; expired or changed actions cannot use an old confirmation. Requested Notion note creation is a write but does not use Gmail's send review.

## 8. Cancel or interrupt

During processing, try **“never mind,” “cancel that,”** or **“stop Bilal.”** The offline English interruption recognizer has a small phrase list; noise, accent, and microphone conditions can affect it.

For manual cancellation, choose **Cancel request** in the tray. Escape cancels an active request when Bilal has focus; when idle it hides the companion. Escape is not monitored globally.

Cancellation stops pending work/speech where possible. It cannot undo completed actions such as opening an app, creating a note, or sending an approved message. Cancelling an active review rejects that reviewed action. For an account operation already in flight, inspect the service before repeating.

## 9. Tray controls

| Item | Purpose |
| --- | --- |
| Show Bilal | Bring the companion above the taskbar |
| Start / finish recording | Start capture or finish early |
| Cancel request | Stop pending work |
| Read reply / type a request | Open conversation and typed input |
| Listen for Hey Bilal | Toggle automatic activation |
| Speak replies | Toggle speech output |
| Collect reviewed wake examples | Start guided local recording/label review |
| Pending approvals | Review waiting actions |
| Last wake was correct | Label the available latest wake sample positive |
| Last wake was a false trigger | Label the available latest wake sample negative |
| Clear conversation | Clear the conversation while idle |
| Quit Bilal | Stop the assistant completely |

Clear conversation does not erase recordings, credentials, or approved memory. These are separate stores. Do not assume tray preferences or a dragged position persist across restarts.

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
| No popup | Check wake toggle/error; use manual recording | Failed/missing offline verification disables activation |
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

A useful report includes exact request, approximate time, transcript, expected/actual result, and error. Avoid sharing secrets or private account content. Recorded artifacts normally share `recordings/command_<id>`: `.wav` audio, `.txt` transcript, and `.answer.txt` reply. Local traces/readiness reports live in ignored `logs/`; they can contain private content too.

## 14. Local readiness check

For local configuration checks and automated regressions without microphone recording or live account actions:

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py --tests
```

The private report is `logs/mvp_readiness.json`. It does not establish physical recognition, audible speakers, actual email delivery, real power transitions, or successful sign-in startup. Complete [field acceptance](FIELD_ACCEPTANCE.md) for those checks.
