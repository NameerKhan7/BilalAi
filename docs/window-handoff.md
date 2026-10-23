# Give an existing window to Bilal

Use this when different browser windows/profiles have different accounts. Launching a Gmail URL in default Chrome does not identify your university account or prove an inbox search happened.

## Continue the university Gmail search

1. Open your university browser yourself. Open Gmail and select the intended university account/tab.
2. Right-click empty space on the Windows desktop and choose **Give control to Bilal**. Windows 11 may put this under **Show more options**. You can also use Bilal's tray menu, or select a failed/blocked task in Task Center and choose **Choose window and continue**.
3. In the dialog, select the failed task. Confirm that its instruction says to search the university inbox for loan emails.
4. Click **Point to a window, then right-click**. A selection overlay appears. Right-click the intended browser window and choose **Give this window to Bilal**.
5. Check the displayed window title and application. Click **Give control and continue this task**.

This creates a new task linked to the old attempt. The previous task's steps remain available for troubleshooting. Completed writes must not be repeated.

The desktop menu starts selection; it does not guess the target browser. A browser's ordinary right-click menu is unchanged. Bilal's selection menu appears only while its explicit selection overlay is active. The selection click is consumed rather than forwarded to the page.

## What access means

- Bilal uses Windows accessibility on that existing window. It does not copy cookies, extract passwords, start remote debugging, or open a new personal browser profile.
- The grant is kept in memory, belongs to one task, and expires. The worker is stopped after at most fifteen minutes of execution. Closing/replacing the window, cancellation, Stop Everything, or exiting Bilal revokes access.
- The selected task cannot launch another app/profile or silently switch to a separately connected Gmail account. One window cannot be controlled by two handed-off tasks at once.
- Generic desktop actions still use the existing review rules. Sending, deletion, authentication and similar sensitive controls are blocked in generic UI automation; supported sensitive workflows retain their dedicated approval path. Window selection alone does not approve them.
- Visible text may be passed to the configured reasoning provider and saved in task results. Selecting a signed-in inbox therefore grants access to its visible content; it is not a local-only analysis mode.

## Gmail search and verification

The selected-browser tools read the actual current URL and accessibility controls. Gmail search preserves the observed account path, such as `/mail/u/2/`, instead of assuming `/mail/u/0/`. A search is verified only when the same account, requested search route, visible query field, and matching visible result labels or an explicit empty-result message can be observed together.

Visible result labels are not full email bodies. Bilal must not claim it read an email in full from those labels. If Gmail needs login, the user signs in manually. If accessibility cannot expose the required controls/results, the task stops without claiming success.

Chrome, Edge, Brave, Firefox, Vivaldi and Opera process names are recognized, but only public Chrome observation has passed a live check in this build. Other browsers, mixed-DPI selection and real Gmail search need field acceptance. Account-preservation and search-verification behavior have automated fixture coverage. This does not establish reliable automation for every application.

## Installation and troubleshooting

From the project directory:

```powershell
.\venv\Scripts\python.exe .\desktop_handoff_menu.py
```

Remove only Bilal's entry with:

```powershell
.\venv\Scripts\python.exe .\desktop_handoff_menu.py --remove
```

The installer changes only Bilal's key under `HKEY_CURRENT_USER\Software\Classes\DesktopBackground\Shell`. It stores a fixed launcher command with `--handoff`; no arbitrary command or window handle is accepted from Explorer. When Bilal is already running, a current-user local pipe opens the handoff dialog in that instance.

For failures, inspect Task Center's recorded steps. A blocked task requesting a window is waiting for human selection, not completed. If the target closed or permission expired, select it again. Elevated, private-browsing and login windows are excluded. Stop Everything is **Ctrl+Alt+Backspace**; it stops pending work without undoing effects already completed.

Run the public Windows check without accessing your accounts:

```powershell
.\venv\Scripts\python.exe .\check_window_handoff.py
```

It opens a temporary Chrome profile on example.com, checks the actual accessibility read and revocation, then closes that test browser. Its local report is `logs/window_handoff_acceptance.json`.

## Code map

| File | Responsibility |
| --- | --- |
| `window_handoff.py` | Task choice, right-click selection overlay, displayed target confirmation |
| `window_grants.py` | Task-bound grants, process/window identity, native revocable property |
| `selected_browser.py` | Existing-window URL observation and verified Gmail search |
| `desktop_worker.py` | Applies window scope again inside the accessibility worker |
| `task_runtime.py` | Resumes work as a linked task, retains the scoped worker across approvals, revokes on completion/cancellation |
| `tool_policy.py` | Rejects tools outside the selected-window scope |
| `handoff_ipc.py` | Current-user command channel that only opens selection UI |
| `desktop_handoff_menu.py` | Installs/removes the current-user desktop entry |
| `tests/test_window_handoff.py` | Grant, scope, search evidence, task state, IPC and cancellation regression tests |
