# Install and run Bilal AI

[Documentation home](README.md) · [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md)

This guide gets the Windows assistant running. Gmail and Notion are optional connections. The project is experimental; successful installation does not establish that every app or voice condition works.

## 1. Prepare the PC

You need Windows, Python **3.11**, Git, a microphone, an audio output device, internet access, and Gemini and Groq API keys with available quota. Install Spotify or Chrome if you intend to use their tools. Desktop automation runs in your signed-in Windows session.

The microphone's local wake checks do not need a cloud service. After activation, recorded commands go to Groq and reasoning uses Gemini. A typed request bypasses microphone recording and Groq.

## 2. Install the project

Open PowerShell in the folder where you want to keep Bilal:

```powershell
git clone https://github.com/NameerKhan7/BilalAi.git
cd BilalAi
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use the virtual environment's Python for subsequent commands. Activating the environment is optional. The cloned repository itself contains `main.py`; you do not need an extra `cd code` after cloning.

## 3. Configure providers

For a new installation only:

```powershell
Copy-Item .env.example .env
notepad .env
```

If `.env` already exists, edit it without copying over it. Enter the values locally:

```dotenv
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
GEMINI_MODEL=
```

A blank model setting selects the project's default. [Configuration](configuration.md) describes precedence and defaults. Do not commit real keys or paste them into issue reports.

## 4. Install local wake verification

```powershell
.\venv\Scripts\python.exe .\setup_wake_verifier.py
```

This downloads Whisper base.en files from a fixed public revision into `models/wake_asr/`. The weight file is about **145 MB**; supporting files require additional space. The installer checks the weight checksum and resumes interrupted downloads when you run it again. It records no audio.

The runtime loads these files locally and does not automatically download them. Without a working verifier, automatic wake activation stays disabled and manual requests remain available.

## 5. Launch and make a harmless request

```powershell
.\venv\Scripts\python.exe .\main.py
```

Bilal starts hidden. Find the tray icon, including the Windows tray overflow area. Say **“Hey Bilal, explain the difference between a website and a web app.”** The companion should appear, capture the command, answer aloud, then hide. Alternatively, use **Read reply / type a request** from the tray.

Keep speech pauses below four seconds during a command. Capturing the full command, transcribing it, reasoning, and speaking are separate stages; a local detection score is not a measure of the whole experience.

If Bilal is already running, use its tray menu to quit before launching an updated version. The app has a single-instance lock.

## 6. Check local readiness

```powershell
.\venv\Scripts\python.exe .\check_mvp_readiness.py
```

The private report is `logs/mvp_readiness.json`. This checks local prerequisites without contacting Gmail or Notion and without recording audio. It does not prove speaker audibility, physical wake accuracy, or successful account operations. See [Testing](testing.md) for regression and field checks.

## Optional: start after Windows sign-in

From the installed project folder:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py
```

This installs the current user's sign-in shortcut. It launches `launch_bilal.pyw` through the environment's `pythonw.exe`, so no console window appears. Startup is after sign-in, not before login. Keep the project and environment at their configured paths; rerun installation if you move them.

To remove the shortcut:

```powershell
.\venv\Scripts\python.exe .\startup_windows.py --remove
```

Verify startup by signing out and back in when convenient. A configured shortcut alone is not a completed sign-in test.

## Optional: connect Gmail

Bilal needs its own OAuth consent, independent of Codex connections. Obtain a **Desktop OAuth client JSON** for a Google project with the Gmail API enabled, then run:

```powershell
.\venv\Scripts\python.exe .\setup_connections.py gmail --client-json "C:\path\to\desktop-client.json"
```

Complete consent in the browser. The setup requests Gmail compose, OpenID, and account email scopes, verifies the account email, then saves credentials encrypted for your Windows user. Sending still requires a draft-specific human approval. Do not use a Gemini key as a Gmail credential.

Live account testing remains pending. Use the authorized account sequence in [Field acceptance](FIELD_ACCEPTANCE.md) when you deliberately choose to validate it.

## Optional: connect Notion

Create an integration with appropriate page permissions and share your intended page with it. Run:

```powershell
.\venv\Scripts\python.exe .\setup_connections.py notion
```

Enter the token at the hidden prompt. Saving a token does not verify its permissions or connect every page in the workspace. Start with a requested read of a shared page; choose the intended parent before asking to create a note.

Next: [Use Bilal](user-guide.md), [Understand each feature](features.md), or [Understand the architecture](architecture.md).
