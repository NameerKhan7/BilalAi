# BilalAI Capability Spec

Product in one line: a voice-first personal agent for Windows that obeys like a butler (Alfred), runs many tasks in the background, delegates to other AI tools, and never does anything irreversible without approval.

Primary user: a solo builder or founder working on a laptop all day. The scenarios in section 11 are examples to test against, not the feature list. The feature list is capabilities: anything a person can do with a laptop, BilalAI must be able to be told to do, within the safety rules in section 3.

## 0. How to use this document

| Rule | Meaning |
|---|---|
| Tiers | P0 = v1 cannot ship without it. P1 = next release. P2 = good to have. P3 = later or maybe never |
| IDs | Every capability has an ID. Reference IDs in commits, tests and task breakdowns |
| Acceptance | Every P0 and P1 row has a test. If it cannot be tested, it is not done |
| Priority | Reliability beats breadth. A smaller set that works every time beats a long set that works sometimes |

## 1. Design principles (for the coding agent)

| # | Principle | What it means in code |
|---|---|---|
| 1 | Deterministic before clever | Prefer CLI, API, file and DOM control over screen clicking. Use vision and coordinate clicking only as a last fallback |
| 2 | Plan, approve, act, verify | Planner produces a task plan. Executor runs steps. Every step ends with a verification check before it is marked done |
| 3 | Everything is a typed tool | Each action is a tool with a name, input schema, risk level, timeout and a verifier. The LLM selects tools, it never runs raw code outside a sandbox |
| 4 | Non-blocking | The user can keep talking while tasks run. No single task may block the voice loop |
| 5 | Content is data, not instructions | Text from web pages, files, emails and other agents' output can never trigger tool calls by itself |
| 6 | Fail loudly and recover | Report failures in one short sentence, keep state, offer retry. Never silently skip |
| 7 | Testable without a microphone | Every voice command can be injected as text so the full suite runs in CI |
| 8 | Provider-agnostic | STT, LLM and TTS sit behind interfaces. Swapping a provider must not touch task logic |
| 9 | Local-first state | Memory, logs, tasks and secrets live on the user's machine unless a feature requires otherwise, and the user can see what leaves |
| 10 | Modest hardware | Baseline target is a 7th gen i7, 16 GB RAM, no GPU. Idle CPU and RAM must be low enough to run at startup |
| 11 | Typed text is exact, voice is intent | Text the user types is a literal payload that no model may rewrite or reformat. Voice and the LLM decide what to do with it, never what it says |
| 12 | See only on demand | Screen capture happens when the user summons it, shows a visible indicator, and frames are not stored by default |

## 2. Capability map

### 2.1 Voice and interaction (VOI)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| VOI-1 | P0 | Push-to-talk activation | Global hotkey. Default path until wake word is proven reliable | 50 trials, at least 98% activate |
| VOI-2 | P0 | Speech to text | Cloud STT behind an interface, with custom vocabulary (app names, project names, people) | 50 scripted commands, at least 90% transcribed correctly |
| VOI-3 | P0 | Multi-command utterances | "Play focus music and ask Claude to read the roadmap" becomes two independent tasks | Utterance with 3 intents creates 3 tasks |
| VOI-4 | P0 | Interrupt and cancel | "Stop", "cancel that", "never mind" halts the current speech and the named or latest task | Stop takes effect in under 1 second |
| VOI-5 | P0 | Spoken status and confirmations | Short replies, no essays. "Done", "Claude finished, want me to send it to Codex?" | Replies under 15 words for routine actions |
| VOI-6 | P0 | Status queries | "What are you doing?", "What's pending?", "Did Claude finish?" | Answers match the task store |
| VOI-7 | P0 | Text input fallback | Same command bar accepts typed input | Same behavior as voice |
| VOI-8 | P1 | Wake word "Hey Bilal" | Only enabled after a fresh independent recording test passes | False activations below 1 per hour of normal use, at least 90% true activation |
| VOI-9 | P1 | Clarifying questions | At most one question, only when the answer changes the action | Never asks more than once per command |
| VOI-10 | P1 | Conversation context | "Do the same for the other file", "send that to him" resolve against recent turns | 10 scripted follow-ups resolve correctly |
| VOI-11 | P2 | Urdu and Roman Urdu commands | Must be benchmarked on the chosen STT first. Published results show Urdu error rates are high without fine tuning | Own benchmark: report WER before promising support |
| VOI-12 | P2 | Voice dictation mode | "Type this" inserts text at the cursor in any app | Works in 5 common apps |
| VOI-13 | P3 | Voice identity (only respond to the owner) | Reduce false triggers and misuse | Later |

### 2.2 Task engine (TSK)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| TSK-1 | P0 | Task objects | ID, goal, steps, state (queued, running, waiting_approval, blocked, done, failed, cancelled), owner tool, timestamps, result | Persisted to SQLite |
| TSK-2 | P0 | Background execution | Tasks run concurrently with a configurable limit | 3 tasks run while the user issues a 4th command |
| TSK-3 | P0 | Cancel, pause, resume | By ID, by name, or "the last one" | State changes correctly and resources are released |
| TSK-4 | P0 | Crash and restart recovery | On restart, running tasks are marked interrupted and offered for resume | Kill process mid task, restart, see the task listed |
| TSK-5 | P0 | Completion notification | Toast plus short voice line, never both if the user is mid sentence | Fires within 2 seconds of completion |
| TSK-6 | P0 | Step verification | Each step has a check (file exists, window title, DOM element, process running, exit code) | Failed check marks the step failed, not done |
| TSK-7 | P1 | Retries with backoff | Only for idempotent steps | Non-idempotent steps never auto retry |
| TSK-8 | P1 | Task dependencies | "When Claude finishes, then start Codex" | B does not start until A is done |
| TSK-9 | P1 | Scheduled and recurring tasks | "Every weekday 9am, brief me" | Fires on time after a reboot |
| TSK-10 | P2 | Triggers | "When a file appears in X", "when I get an email from Y" | Later |

### 2.3 Computer control (CTL)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| CTL-1 | P0 | App launch, focus, close, switch | Installed app discovery by name with fuzzy match | 20 common apps open and focus correctly |
| CTL-2 | P0 | Window management | Snap, move, minimize, maximize, list open windows | Matches Windows state |
| CTL-3 | P0 | Clipboard read and write | Core primitive for handing text between apps | Round trip of 100 KB text |
| CTL-4 | P0 | Keyboard input | Type text, send shortcuts, with focus verification before typing | Never types into the wrong window |
| CTL-5 | P0 | Browser control | DOM level control (Playwright or similar), tab management, form filling, page reading | Works on 5 test sites |
| CTL-6 | P0 | Media control | Spotify and system volume, play, pause, skip, queue | Verified playback state |
| CTL-7 | P0 | File operations inside allowed folders | Read, create, move, copy, search. Delete goes to recycle bin | Cannot touch paths outside the allow list |
| CTL-8 | P1 | Accessibility tree control | Windows UI Automation to read and click named controls | Works in 10 common apps |
| CTL-9 | P1 | Screenshot and vision check | Screenshot a window and ask a vision model whether the goal state is reached | Used as verifier, not primary controller |
| CTL-10 | P1 | System actions | Volume, brightness, do not disturb, lock. Sleep, shutdown, restart need confirmation | Confirmation required |
| CTL-11 | P2 | Coordinate clicking by vision | Last resort for apps with no accessibility tree | Flagged as fragile |
| CTL-12 | P2 | Multi monitor and virtual desktop awareness | Place windows on the named monitor | Later |
| CTL-13 | P2 | Shell command execution | Only through a sandbox with an allow list, always L2 or higher | Never raw shell from LLM text |

### 2.4 Agent orchestration (AGT): the delegator

This is the capability that makes BilalAI more than a launcher.

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| AGT-1 | P0 | Run Claude Code non-interactively | Use its scriptable mode (`claude -p`, with piped input and JSON output options). Verify flags against current docs at build time | Prompt in, structured result out |
| AGT-2 | P0 | Run Codex non-interactively | Use `codex exec`. It defaults to a read-only sandbox, which matches the approval design | Prompt in, final message out |
| AGT-3 | P0 | Result capture and storage | Full output stored as an artifact linked to the task. Voice reads a summary only | Output retrievable by task ID |
| AGT-4 | P0 | Relay between agents | "Take Claude's plan and give it to Codex" moves the stored artifact into the next agent's prompt without the user touching a clipboard | Plan from A appears verbatim in B's input |
| AGT-5 | P0 | Approval gate before write access | Planning runs read only. Execution with write permission requires approval of the plan first | No write access without an approval event in the log |
| AGT-6 | P0 | Working directory and context pack | Each agent run gets a project folder and a context pack (files the user named) | Agent sees only the allowed project folder |
| AGT-7 | P1 | Session resume | Continue a previous agent session by ID ("continue that") | Resume works across restarts |
| AGT-8 | P1 | Parallel agents | Run two agents on different tasks at once with a concurrency cap | No cross talk between sessions |
| AGT-9 | P1 | Usage and cost tracking | Track calls and credits per agent. Subscription headless usage may draw from separate allowances, so surface remaining budget | Daily usage report |
| AGT-10 | P1 | Output parsing into tasks | Turn a plan into a task checklist the user can reorder | Checklist matches plan items |
| AGT-11 | P2 | GUI fallback for chat apps without an API | Drive the desktop chat app through accessibility or browser control, clearly marked as fragile | Documented failure modes |
| AGT-12 | P2 | Review loop | After an agent finishes, a second agent reviews the diff and reports | Optional per task |
| AGT-13 | P2 | MCP client support | Connect external tool servers through MCP | At least 1 server working |

### 2.5 Memory and context (MEM)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| MEM-1 | P0 | Preferences store | Default apps, folders, music, voice, approval settings | Survives restart |
| MEM-2 | P0 | Project profiles | A named project maps to folders, repos, docs, preferred agent, notes | "Work on Elevra" selects the right context |
| MEM-3 | P1 | Long term memory | Facts and habits the user states, editable and viewable | User can list and delete any memory |
| MEM-4 | P1 | Writing style profile | Samples of the user's emails and posts to match tone in drafts | Drafts accepted without edit at least 60% of the time in dogfooding |
| MEM-5 | P1 | Contact book | Names, relationships, channels, notes | "Email Ali" resolves unambiguously or asks once |
| MEM-6 | P1 | Local document search | Index chosen folders (md, txt, pdf, docx) | Query returns correct file |
| MEM-7 | P2 | Session summaries | End of day summary of what was done | Later |
| MEM-8 | P3 | Cross device sync | Later |

### 2.6 Work integrations (INT)

All outbound communication is draft first. Sending is always an approval action.

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| INT-1 | P1 | Gmail | Read, search, summarize, draft, and send after approval | Draft appears in Gmail, send logged |
| INT-2 | P1 | Notion | Create and update tasks, notes and pages | Entry appears with correct properties |
| INT-3 | P1 | Calendar | Read schedule, find free time, create events after approval | Event matches request |
| INT-4 | P1 | Outreach pipeline | List of targets, status, draft per person, follow-up reminders, no auto send | Batch of 20 drafts reviewed in one approval screen |
| INT-5 | P2 | WhatsApp drafting | Prepare text and copy it, the human sends. Check platform terms before any automation of sending | Draft ready on clipboard |
| INT-6 | P2 | Content assistant | Hooks, scripts, structure, content calendar entries | Output saved to a named place |
| INT-7 | P2 | Google Drive and Sheets | Read and write files and rows | Later |
| INT-8 | P2 | Messaging apps (Slack, Discord) | Read and draft | Later |
| INT-9 | P2 | Social posting | Draft and schedule, publish only after approval | Later |
| INT-10 | P3 | Payments, invoicing | Out of scope for v1. Highest risk category | Never auto |

### 2.7 Personas and skills (EXT)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| EXT-1 | P1 | Skills folder | Drop in a skill (instructions plus tool bindings) and it becomes available | New skill works with no code change to core |
| EXT-2 | P2 | Employee personas | Named personas (for example marketing, operations) with their own prompts, memory slice and scoped permissions | A persona cannot use tools outside its scope |
| EXT-3 | P2 | Skill sharing format | Export and import skills | Later |
| EXT-4 | P3 | Marketplace | Only after real users exist | Later |

### 2.8 Quick input panel (QIN): exact text plus spoken instruction

Why it exists: speech to text corrupts exact strings (email addresses, URLs, codes, names, case sensitive values). The user types the exact data, then tells Bilal what to do with it by voice.

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| QIN-1 | P0 | Double click the avatar to open the panel | Input field appears next to the avatar with focus already inside. Esc closes it | Opens in under half a second, typing works immediately |
| QIN-2 | P0 | Literal payload | Whatever is typed is stored as an exact string. No STT, LLM, autocorrect or formatting step may change it | 20 test strings (emails, URLs, codes, mixed case, symbols) arrive byte for byte in the target |
| QIN-3 | P0 | Speak while the panel is open | The panel stays open while the user speaks, and the spoken instruction is combined with the panel content. "Hey Bilal, I added some things in the text, read it and do it accordingly" must work, and so must "send the file to this address" | Instruction that refers to the panel content resolves to the right literals |
| QIN-4 | P0 | Placeholder substitution | The LLM sees labeled slots (for example LIT_1 with a short description), not the raw string. The executor substitutes the exact text locally at the moment of action | Prompt traces show slots, target app shows the exact text |
| QIN-5 | P0 | Secret handling | Detect likely secrets (passwords, API keys, tokens, card numbers). By default they never enter LLM prompts, logs or memory. They are only substituted locally at action time. Sending a secret to a cloud model needs explicit L2 approval | Scan of logs, prompt traces and memory finds none |
| QIN-6 | P0 | Typed only commands | The panel also works with no voice at all, through the same engine as voice | Same result as the spoken version |
| QIN-7 | P1 | Several labeled snippets | Each line or chip becomes its own slot (email, link, code) with an optional label | "Use the second link" resolves correctly |
| QIN-8 | P1 | Attachments | Paste an image, drop a file, paste clipboard content. Attachments are referenced like literals | File reaches the task intact |
| QIN-9 | P1 | Literal verification on approval | When a literal is a recipient, URL or amount, the approval card shows it in a monospace font, with look alike characters highlighted | Look alike test strings are flagged |
| QIN-10 | P1 | Panel history | Recent non secret entries can be recalled, and cleared in one click | Secrets never appear in history |
| QIN-11 | P2 | Dictation into the panel with exactness marking | Dictated text is shown as approximate, typed text as exact, so the user knows what to double check | Visual difference is clear |
| QIN-12 | P2 | Spell mode for voice only entry | "Spell it" accepts letter by letter input ("a as in apple") for when typing is not possible | Correct on 10 test strings |

### 2.9 Summon and hotkeys (HOT)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| HOT-1 | P0 | Configurable global summon hotkey | Works from any app. The current choice is Ctrl+Shift, see the technical note below | Registers, fires, and can be changed in settings |
| HOT-2 | P0 | Summon behavior | On press: avatar appears, microphone starts, clear listening state. Listening ends on silence, key release (hold mode), second press, or Esc | Each exit path works |
| HOT-3 | P0 | Hold to talk and press to toggle | User picks the mode | Both modes pass 50 trials each at 98% or better |
| HOT-4 | P0 | Instant feedback | A visual or audible cue appears the moment the key is pressed, before any network call | Cue appears with no perceptible delay |
| HOT-5 | P0 | Works over full screen apps and documented limits with elevated (admin) windows | Test and write down what fails | Limits listed in the README |
| HOT-6 | P1 | Separate bindings | Remappable keys for: summon, quick input panel, pointer mode, stop everything (SAF-3) | All remappable, no overlaps allowed |
| HOT-7 | P1 | Conflict detection | Warn when the combo clashes with a Windows shortcut or another app. Check Windows input language switching, which can use Ctrl+Shift or Alt+Shift when several layouts are installed | Warning shown for a known clash |
| HOT-8 | P2 | Gestures while summoned | Tap versus hold, double tap for the quick input panel | Later |

Technical note on the hotkey for the coding agent:

| Fact | Consequence |
|---|---|
| The standard Windows hotkey API (RegisterHotKey) cannot register a modifier only combination, and it does not report key release | Ctrl+Shift alone and true hold to talk both need a low level keyboard hook |
| A low level hook sees every keystroke on the machine and runs before the focused app | Keep the handler tiny on its own thread, never log keys, expect antivirus attention, and never let it slow typing |
| A chord with a normal key (for example Ctrl+Shift+Space) can use the standard API for toggle mode | Default to a chord. Offer modifier only (Ctrl+Shift) as an opt in using the hook |

### 2.10 Screen awareness and the Bilal cursor (SCR)

Build in this order. Each phase must work before the next starts.

| Phase | Goal |
|---|---|
| A | Bilal can see the screen when asked |
| B | The user can point at things with the Bilal cursor and ask about them |
| C | Live screen share for continuous awareness |
| D | Bilal points back and walks the user through tasks |

Phase A: see the screen

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| SCR-1 | P1 | On demand screen capture | "What's on my screen?" captures the active window (default) or the full screen, sends it to a vision capable model, and answers | Accurate description of 10 test screens |
| SCR-2 | P1 | Capture scope | Active window, full screen, chosen monitor, or a region | All scopes work |
| SCR-3 | P1 | Visible capture indicator | Every capture shows an indicator and is logged. No hidden capture | Indicator shown on 100 percent of captures |
| SCR-4 | P1 | Frames not stored by default | Kept in memory only for the request. Saving is opt in per task | No image files on disk after a normal run |
| SCR-5 | P1 | Sensitive window guard | Windows on a user editable block list (password managers, banking, private browsing) are skipped or blurred | Blocked window never leaves the machine |
| SCR-6 | P1 | Hybrid grounding | Use the accessibility tree first, local OCR second, vision model third. Cheaper, faster and more accurate than vision alone | Per capture log shows which layer answered |

Phase B: the Bilal cursor

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| SCR-7 | P1 | Pointer mode toggle | While summoned, a configurable key or click turns on the Bilal cursor: a distinct marker that follows the mouse on a transparent click through overlay, with a clear on and off state | State is always visible |
| SCR-8 | P1 | Click to ask | In pointer mode a click captures a frame, records coordinates, window, and the element under the cursor from the accessibility tree (name, role, value), crops around the point, and answers "what is this?" by voice plus a small bubble. A spoken question replaces the default question | Correct on at least 90 percent of a 20 element test |
| SCR-9 | P1 | Safe click | In pointer mode the click is intercepted. The underlying app never receives it | Click a destructive looking button, nothing happens in the app |
| SCR-10 | P1 | Region select | Drag a box around text, a chart or an image and ask about it | Works over multiple apps |
| SCR-11 | P1 | Point then command | "Fix this", "copy this", "explain this" use the pointed target as context. Any action still goes through the autonomy policy | Risky actions still ask |
| SCR-12 | P2 | Multi point | Click several things in sequence ("compare this and this") before the question ends | Both targets are in the answer |

Phase C and D

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| SCR-13 | P2 | Live screen share | User started, visibly active, time limited session with low frame rate and change detection so Bilal can follow what is happening. Costs are capped | Stops on time, shows a running indicator |
| SCR-14 | P2 | Guided pointing | Bilal draws an arrow or highlight and moves its own cursor to walk the user through a task ("click here, then here") without clicking for them | User completes a 5 step task in an unfamiliar app |
| SCR-15 | P2 | Click for me | "Click this" performs the click on the pointed target, verified afterwards (CTL-8, CTL-9), risky targets need approval | Verified result |
| SCR-16 | P2 | Local OCR as the first resort | Simple "read this" needs no cloud call, which saves cost and keeps content private | Works offline |
| SCR-17 | P3 | Screen recording into tutorials or summaries | Later |

## 3. Trust and safety (SAF): non negotiable

BilalAI is "a servant that must obey," but obedience is bounded. The user's instruction is authority. Content the agent reads is not.

### 3.1 Autonomy levels

| Level | Behavior | Examples |
|---|---|---|
| L0 Auto | Do it, brief confirmation | Open an app, play music, read an allowed file, web search, take a screenshot |
| L1 Act then tell | Do it, report what changed, offer undo | Create a draft, write a note, create a file inside the workspace |
| L2 Ask first | Show a one screen approval card, act only on yes | Send any email or message, run an agent with write access, delete files, install software, post publicly, use credentials, run shell commands |
| L3 Hard confirm | Typed or two step confirmation, cooldown, never batched | Bulk sends, financial actions, changing security settings, anything outside the allow list |

Users can adjust a tool's level. They can promote a repeated L2 action to L1 after they choose to. The system never promotes on its own.

### 3.2 Safety capabilities

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| SAF-1 | P0 | Policy engine | Every tool call passes through one function that checks level, allow lists and approval state | No tool executes without a policy decision logged |
| SAF-2 | P0 | Approval card | One screen: what will happen, which files or recipients, what is irreversible. Approve, edit, or reject. Batch approval for plans | 1 approval per plan, not per step |
| SAF-3 | P0 | Kill switch | Global hotkey and voice "stop everything" cancels all tasks and stops agents | All child processes terminated in under 2 seconds |
| SAF-4 | P0 | Audit log | Append only record of every command, plan, approval, tool call and result, viewable in the UI | Can reconstruct any action |
| SAF-5 | P0 | Allow lists | Folders, domains, apps and recipients the agent may touch | Out of list access is blocked and logged |
| SAF-6 | P0 | Prompt injection defense | Untrusted content is wrapped and labeled as data. Tool calls caused by untrusted content require approval | Test pages with hidden instructions cannot trigger actions |
| SAF-7 | P0 | Secrets handling | Keys in the Windows credential store, never in logs, prompts or the repo. Redaction in logs | Secret scan of logs and repo is clean |
| SAF-8 | P1 | Undo | Recycle bin for deletes, draft deletion, file version snapshots before agent edits | Undo restores previous state |
| SAF-9 | P1 | Data egress visibility | Settings page shows which provider receives audio, text and files | Matches actual network calls |
| SAF-10 | P1 | Rate limits | Cap sends, agent runs and spend per hour and per day | Limit blocks and tells the user |
| SAF-11 | P1 | Dry run mode | Show the plan and the exact actions without executing | Zero side effects |
| SAF-12 | P2 | Local only mode | Local STT and local LLM, accepting lower quality | Later |
| SAF-13 | P2 | Sensitive window guard | Never read or type into password managers, banking pages or private windows | Blocked by default |
| SAF-14 | P0 | Screen features are user triggered | Capture only after a user action (hotkey, pointer click, explicit command). No background capture by default | Idle machine produces zero captures |
| SAF-15 | P1 | Screen content is untrusted data | Text on screen can contain instructions aimed at the agent. Treat it exactly like web content (SAF-6) | Screen with hidden instruction text triggers nothing |
| SAF-16 | P2 | Redaction before sending | Blur detected secrets and sensitive windows in frames before they leave the machine | Test frames show blurred regions |

## 4. Reliability and operations (REL)

| ID | Tier | Capability | Detail | Acceptance test |
|---|---|---|---|---|
| REL-1 | P0 | Benchmark suite | 50 scripted commands with expected end states, run from text injection | Report pass rate on every build |
| REL-2 | P0 | Structured logging and traces | One trace per command from utterance to final result | Searchable by task ID |
| REL-3 | P0 | Graceful degradation | If STT or LLM is down, say so, switch to text or queue the task | No crash on provider failure |
| REL-4 | P0 | Silent startup and tray control | Launch at sign in, single instance, pause and quit from tray | Starts without a console window |
| REL-5 | P1 | Resource budget | Idle usage low enough to leave running all day | Measured and reported |
| REL-6 | P1 | Health check screen | Mic, network, providers, accounts, permissions, versions | One screen shows all green or the failing item |
| REL-7 | P1 | Auto update with rollback | Signed updates | Later |
| REL-8 | P2 | Opt in diagnostics | User controlled, no content by default | Later |

## 5. Shipping and product basics (SHP)

| ID | Tier | Capability | Detail |
|---|---|---|---|
| SHP-1 | P1 | Installer | One installer, no Python or manual setup. Guided key setup |
| SHP-2 | P1 | First run onboarding under 10 minutes | Mic test, connect accounts, pick folders, run one real sample task |
| SHP-3 | P1 | Licensing review | Confirm every model, dataset and library allows commercial use before any paid release. Some wake word training assets are noncommercial |
| SHP-4 | P1 | Clear privacy notice | Plain language: what leaves the device and why |
| SHP-5 | P2 | Pricing and billing | Decide after dogfooding. Existing dictation tools cost roughly 12 to 15 dollars per user per month, which is the price anchor |
| SHP-6 | P2 | Bring your own keys versus hosted | Decide based on cost per user |

## 6. Standard flows (build these exact flows first)

### Flow A: Delegate and relay (core)

| Step | System behavior |
|---|---|
| 1 | User: "Ask Claude to read the roadmap and break down this week's work." Creates task T1 (AGT-1, read only, project context pack) |
| 2 | User keeps working. T1 runs in background |
| 3 | T1 completes, notification: "Claude finished the breakdown. Want to see it?" Result stored as an artifact |
| 4 | User: "Give it to Codex." Creates T2 with T1's artifact as input, plan phase read only |
| 5 | Approval card: plan, target folder, files likely to change, write access requested. User approves once |
| 6 | T2 executes with write access inside the project folder only. Snapshot taken first |
| 7 | Completion notification with summary and diff location. Audit log complete |

### Flow B: Draft and approve outreach

| Step | System behavior |
|---|---|
| 1 | User names a target list or project |
| 2 | System creates one draft per recipient in the user's style, nothing sent |
| 3 | One review screen lists all drafts, user edits or rejects each, then approves the batch |
| 4 | Sends respect rate limits, results logged, follow up reminders created |

### Flow C: Parallel conversation

| Step | System behavior |
|---|---|
| 1 | While T1 runs, user says "Play focus music". Runs instantly as L0 |
| 2 | User asks "What's pending?" and gets a one line status |
| 3 | User says "Cancel the Codex task". Only that task stops |

### Flow D: Typed exact data plus spoken instruction

| Step | System behavior |
|---|---|
| 1 | User double clicks the avatar. Input panel opens with focus in the field |
| 2 | User types the exact data (for example a recipient address and a link) |
| 3 | User says "Hey Bilal, I added some things in the text, read it and do it accordingly" |
| 4 | System builds the request: instruction from voice, literals from the panel as slots. The LLM plans with placeholders only |
| 5 | Approval card shows the exact literal strings in monospace, with look alike characters flagged |
| 6 | Executor substitutes the exact strings locally and acts. Logs store redacted forms of anything secret |

### Flow E: Summon, look, point

| Step | System behavior |
|---|---|
| 1 | User presses the summon hotkey. Avatar appears and listens |
| 2 | User asks "What's on my screen?" Active window is captured with a visible indicator, answer is spoken |
| 3 | User turns on pointer mode. The Bilal cursor appears over the screen |
| 4 | User clicks an element while asking "what is this?" Click is intercepted, element is identified (accessibility tree first, then OCR, then vision), answer is spoken with a bubble at the click point |
| 5 | User says "click this for me". The action goes through the autonomy policy, then is verified |

## 7. Situations to test against (not a feature list)

Each situation must work end to end. They exist to expose gaps in the capabilities above.

| # | Situation | Capabilities exercised |
|---|---|---|
| S1 | Morning kickoff: "Open my project, brief me on today, start focus music" | MEM-2, INT-3, CTL-1, CTL-6, VOI-3 |
| S2 | Mid work interruption: user asks a new question while an agent run is in progress | TSK-2, VOI-6, VOI-4 |
| S3 | Plan to build handoff across two different AI tools | AGT-1, AGT-2, AGT-4, AGT-5, SAF-2 |
| S4 | Investor outreach batch with follow ups next week | INT-1, INT-4, SAF-10, TSK-9 |
| S5 | Content session: brainstorm hooks while the user is away, results waiting on return | INT-6, TSK-5, MEM-4 |
| S6 | A web page the agent reads contains hidden instructions | SAF-6, SAF-4 |
| S7 | Internet drops mid task | REL-3, TSK-4 |
| S8 | User says "stop everything" during a write phase | SAF-3, SAF-8 |
| S9 | Ambiguous command ("send it to him") | VOI-9, VOI-10, MEM-5 |
| S10 | End of day: "What did you do today?" | SAF-4, MEM-7 |
| S11 | Exact email address typed in the panel, voice says "send the file to this address" | QIN-2, QIN-3, QIN-4, QIN-9, INT-1, SAF-2 |
| S12 | API key typed in the panel, "add this to the env file". Key never reaches cloud logs | QIN-5, SAF-7 |
| S13 | Summon hotkey pressed while a full screen app is active | HOT-2, HOT-5 |
| S14 | Pointer click on a settings toggle. Bilal explains it, the toggle does not change | SCR-8, SCR-9 |
| S15 | A password manager window is open while the user asks "what's on my screen?" | SCR-5, SAF-13 |
| S16 | A page on screen contains hidden instructions aimed at the agent | SAF-15, SAF-6 |

## 8. Non goals for v1

| Not doing | Reason |
|---|---|
| Auto sending outbound messages without approval | One bad send costs more than the time saved |
| Payments and financial actions | Highest risk, lowest frequency |
| Mobile app, multi user, marketplace | No evidence of demand yet |
| Always listening transcription of everything | Privacy cost, no benefit |
| Visual polish beyond status clarity | Reliability first |
| Claiming Urdu support before measuring it | Accuracy is unproven |
| Hidden or continuous screen recording | Privacy and legal risk. Screen sharing is user started and visible |
| Clicking on screen without approval for risky targets | Same rules as every other action |

## 9. Definition of done for v1

| Gate | Pass condition |
|---|---|
| Benchmark | At least 90% pass on the 50 command suite |
| Dogfooding | Owner uses it daily for 7 days, 20 consecutive successful Flow A runs |
| Safety | Zero unapproved L2 actions in the audit log. Injection tests (S6) all blocked |
| Setup | Fresh Windows machine to first successful command in under 10 minutes |
| Honesty | Known failures documented in the README |
| Exact input | 20 literal strings arrive byte for byte, zero secrets in logs or prompt traces |
| Screen | Click to ask correct on at least 90 percent of a 20 element test, and pointer clicks never trigger the underlying app |

## 10. Open decisions for the owner

| Decision | Why it matters |
|---|---|
| Which LLM provider handles planning versus execution | Cost, quality and rate limits |
| Bring your own keys or hosted | Affects pricing, support and privacy |
| Windows only in v1 | Keeps scope small, confirm |
| Open source license and what stays paid | Decides the business model |
| First external users | Pick 5 real people, collect their top 5 repetitive tasks, compare against this spec |
| Hotkey: modifier only (Ctrl+Shift) or a chord | Modifier only requires a keyboard hook and may clash with Windows shortcuts |
| Vision provider and monthly cost cap per user | Screen features multiply model costs, and frames leave the machine |
