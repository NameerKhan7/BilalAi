# Design decisions

[Documentation home](README.md) · [Architecture](architecture.md) · [Code reference](code-reference.md)

These decisions describe the implementation reviewed on 22 October 2026. They are explanations of the present design, not promises that every future feature must use the same approach.

## 1. A model-led tool loop handles requests

**Decision:** `RequestProcessor` forwards requests to `AgentBrain.run`. The model can select declared tools, inspect their results, and decide its next step within a bounded loop.

**Reason:** a phrase-to-command table cannot reliably handle paraphrases, missing details, or multi-step tasks. An agent needs feedback from the environment after taking an action.

**Tradeoff:** the model can misunderstand intent, and it can only act through the tools actually implemented. An LLM does not create access to an unsupported app. New capabilities require a tool or an accessible interface, validation, and tests. There is no arbitrary shell execution tool.

## 2. Wake activation requires more than a classifier score

**Decision:** the ONNX wake classifier and temporal gate produce candidates. A local, pretrained Whisper verifier checks for the full phrase before automatic command capture proceeds. The final command transcript is checked for the wake phrase as well.

**Reason:** background sounds and ordinary speech produced false activations. A second phrase check provides another filter before an agent task starts.

**Tradeoff:** verification adds latency and can reject real attempts. The verifier uses the context prompt `Hey Bilal.` with a confidence cutoff; it is not an unbiased speaker-recognition system. A video saying the actual phrase can still activate Bilal. Missing verifier assets disable automatic wake activation rather than bypass the check.

See [configuration](configuration.md) and [field acceptance](FIELD_ACCEPTANCE.md) before tuning this behavior.

## 3. Desktop actions use observed controls

**Decision:** Windows accessibility observation provides app/window/control information. Worker processes execute supported actions using observed identifiers. Spotify has a dedicated workflow with playback readback.

**Reason:** actions should refer to what the system currently exposes, and success should have evidence beyond a click being attempted.

**Tradeoff:** inaccessible or custom-drawn controls may not be usable. This version has no general screenshot-vision fallback. Control identifiers can become stale after an action, requiring another observation. Spotify playback verification is stronger than a general claim that every desktop action can be verified.

## 4. Sensitive final actions belong to the approval UI

**Decision:** the model can propose an email send, memory change, or power action through the relevant workflow. The trusted local UI handles approval. Pending actions are persisted with a payload digest and claimed once before execution.

**Reason:** the user must review the actual action, and a stale or duplicated approval must not silently execute a different payload.

**Tradeoff:** interruption, expiry, or an ambiguous network result may require another review or manual inspection. Cancellation cannot undo an effect that has already occurred. Email sending and system power execution are not directly exposed as model tools.

## 5. Account connections belong to the standalone app

**Decision:** Gmail OAuth credentials and the Notion integration token use Windows DPAPI storage under the current Windows user. Setup is explicit through `setup_connections.py`.

**Reason:** account access must be available to Bilal itself, including when launched at sign-in. Codex's connectors are a separate application's connections.

**Tradeoff:** setup is required on the target Windows account. Encrypted credentials do not make transcripts, traces, or the SQLite database encrypted. See [data and security](data-and-security.md).

## 6. Learning produces reviewed candidates

**Decision:** collected wake clips need explicit review and valid file hashes. Evaluation and candidate training stay separate from the deployed wake model.

**Reason:** an automatic activation is not proof that a clip is a positive example. Training on unreviewed detections could reinforce false activations.

**Tradeoff:** improvement needs user feedback, balanced sessions, and fresh evaluation. This is not continuous autonomous retraining, and saving a preference is not training an ML model.

## 7. The companion stays out of the way

**Decision:** a small Qt companion starts hidden and appears during interaction. Details, settings, and manual controls live behind the tray or contextual dialogs. Animation uses supplied 2D poses and procedural movement.

**Reason:** the assistant should fit around the user's work while still showing its state and requesting missing information when necessary.

**Tradeoff:** it is not a fully rigged 3D character. Hidden startup can look like a failed launch unless the user knows to check the tray. Windows sleep suspends the process, so Bilal cannot hear a wake phrase while the PC is asleep.

## Recording future decisions

When an architectural change introduces a meaningful tradeoff, add a dated entry explaining the problem, the decision, the alternative considered, its consequences, and the tests or acceptance evidence. Update the current architecture and feature guides too; a decision log is not a replacement for them.
