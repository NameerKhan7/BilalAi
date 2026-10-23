# Capability build validation — 23 October 2026

[Capability matrix](CAPABILITY_STATUS.md) · [Task architecture](task-system.md) · [Testing guide](testing.md)

This report records what was actually checked. It is not full acceptance of the 138-capability specification.

## Existing-window handoff follow-up

- The complete regression suite passes **216 tests** after the handoff changes, including 21 handoff tests covering account preservation, evidence requirements, task scope, stale/revoked grants, exclusive window ownership, linked task continuation and the local UI command channel.
- A real temporary Chrome profile on example.com passed native window binding, accessibility URL/title observation and refusal after revocation. The test closed its own browser and did not access personal accounts. Reproduce with `check_window_handoff.py`; its private local report is under `logs/`.
- The current-user desktop menu was installed and its fixed launcher command read back. The restarted production app reports `window_handoff: true`, the left Ctrl + left Shift shortcut and a registered hook. The local command successfully opened its handoff dialog.
- Live university Gmail search, other browsers and physical mixed-DPI selection remain pending. See [the handoff guide](window-handoff.md). These checks do not establish that every desktop app can be automated.

## Earlier foundation checks

| Check | Result | Scope |
| --- | --- | --- |
| Final full regression | **195 passed in 22.078 seconds** | Native Windows, simulated providers/external effects where documented |
| Real Gemini queue | Passed | One ordinary answer through planner, background worker and temporary durable storage |
| Real Codex delegation | Passed | Read-only, tool-disabled prompt produced final answer and usage |
| Claude installation | 2.1.309 installed; flags checked | Live use needs an Anthropic key; no prompt sent |
| Native keyboard hook | Registered and released | Does not replace 50 physical activation trials per mode |
| Clipboard | 100,000-byte round trip verified | Original Unicode clipboard restored; no content printed/uploaded |
| Owned Chrome | Five sites opened and read | example.com, www.python.org, docs.python.org, en.wikipedia.org, www.wikipedia.org; not form/click acceptance |
| Provider key migration | Gemini/Groq encrypted storage readback passed | Real values excluded from public files |
| Publishable-file credential check | No known project provider key values found in 138 public files | Not an exhaustive unknown-secret detector or historical Git scan |
| Documentation links | No broken relative links in publishable Markdown | Local-file targets checked |
| Running assistant | Hidden 96 × 120 avatar, task runtime enabled, SAPI available, hook registered | Wake off; default left Ctrl+Shift+Space chord |
| Short idle sample | 0.0% process CPU over two seconds; 146.2 MB resident memory | One machine/sample, not a representative resource benchmark |

The exact-input foundation subset also passed all **27 checks** after the final token-masking refinement.

Automated checks include durable tasks/dependencies, cancellation, restart handling, approved deterministic batches, edited-plan invalidation, approval revocation, encrypted file undo, twenty exact file payloads, secret-slot substitution without database leakage, UI notice deferral, screen opt-in and sensitive-window guards. The pointer test consumes a simulated Qt event without forwarding it; it does not prove physical interception over all Windows applications.

No real screenshot was captured/uploaded during these checks. No email was sent, live Notion content created, calendar account connected, or power action performed. Existing account acceptance remains pending by the owner's earlier choice. The new Windows GitHub Actions workflow is configured; a successful hosted run must be observed separately.

Still required: the real 50-command semantic benchmark, fresh microphone/STT/hotkey/wake trials, screen accuracy/interception tests, representative full-screen/elevated/mixed-DPI coverage, reviewed external-agent writes with project isolation, remaining work integrations, installer/licensing review and seven-day dogfooding. P2/P3 items remain future scope. The matrix records these individually.
