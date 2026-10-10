# Six-area baseline — before implementation

Date: 2026-10-11 (Asia/Karachi).

| Area | Baseline finding | Evidence / limit |
|---|---|---|
| Wake activation | Experimental; fresh field validation needed | Two existing calibration reports: 2/5 positives with 0/5 negative hits at 0.80; another model/profile reported 4/5 positives and 1/8 negative hits at 0.30. Labels include a user-reported wrong phrase, so these are not reliable general accuracy estimates. |
| Pauses/cancellation | Pause handling passes; spoken cancellation missing | Existing pause tests pass. A diagnostic 'Never mind' request reached the agent instead of cancelling. Windows has an en-US offline recognizer available. |
| Controlled learning | Missing | memory.py is empty; no persistent confirmed preferences or wake-label ledger. |
| Execution/browser | Partial | Observe-act-verify loop and stale-control checks pass; no webpage-reading tool. |
| Gmail/Notion | Missing and live tests blocked | No runtime connector tools or Gmail/Notion credentials. User chose build-first and deferred live account tests. |
| Reliability | Existing suite passes, scope incomplete | 57 tests pass, including shutdown/startup/recording. Broad physical voice/noise scenarios and account workflows are not established. |

Test private audio locally only. Keep new account tests pending until the user connects Bilal itself. Do not count mocks or old calibration recordings as independent real-world success rates.
