<table align="center" width="100%" cellpadding="18" cellspacing="0" bgcolor="#3E5A73">
  <tr>
    <td align="center">
      <img src="assets/logo.png" alt="Persia logo" width="220">
    </td>
  </tr>
</table>

# Persia - Local-First Voice AI Assistant

Persia is a local-first voice assistant designed to turn natural-language requests into safe, structured actions across personal productivity tools. The system combines an offline speech pipeline, a locally hosted language model, persistent memory, tool routing, confirmations for consequential actions, and optional integrations for email, calendars, Slack, files, notes, tasks, browser workflows, and PDF documents.

> **Public repository note:** This repository is a public engineering snapshot. The private voice-agent runtime, credentials, runtime memory, training data, model weights, generated artifacts, and internal planning documents are intentionally excluded. The README documents the full system, while the published code focuses on the browser bridge and fine-tuning utilities.

## Why This Project

Persia explores the engineering problems that appear when an AI assistant must operate on real user data:

- Converting speech into reliable actions instead of free-form text responses
- Selecting specialized tools from a large catalog of structured schemas
- Executing multi-step requests through a ReAct-style loop
- Asking for confirmation before sending, deleting, creating, or posting
- Keeping inference, audio processing, and memory local by default
- Preserving user-stated facts separately from model-generated inferences
- Exposing progress and session state through a local web interface

## System Architecture

```text
Microphone
    -> Wake-word detection
    -> Voice activity detection
    -> Speech-to-text
    -> Memory retrieval
    -> Local LLM and tool router
    -> ReAct tool loop
    -> Response splitter
    -> Text-to-speech
    -> Speaker
```

The core runtime uses Python, Ollama, Faster-Whisper, Kokoro TTS, Silero VAD, SQLite, and FastAPI. Inference, audio processing, and memory storage run locally. Optional integrations contact third-party services only when explicitly configured by the operator.

## Capabilities

| Area | Examples | Design focus |
| --- | --- | --- |
| Files | List, read, write, edit, search, delete | Allowed-directory enforcement and confirmation for destructive actions |
| Calendar | Read and manage events | Apple CalDAV and Google Calendar support |
| Email | Read, search, send, reply, forward, trash | Read-before-send workflow and explicit confirmation |
| Notes and todos | Obsidian notes and task lists | Markdown/YAML notes and named todo lists |
| Google Tasks | Lists, create, update, complete, delete | Natural-language due dates and list-aware routing |
| Slack | Read channels and threads, search, post, reply | Socket Mode integration without a public inbound endpoint |
| Memory | Remember, recall, correct, forget, remind | Persistent multi-tier memory with conflict handling |
| Browser | LinkedIn jobs, profiles, inbox, and page text | Local Chrome extension bridge and DOM extractors |
| Documents | Read PDFs and fill forms | Digital PDFs, AcroForms, scanned OCR, and form-field detection |
| System | Selected commands, glob, and grep operations | Command allowlisting and blocklist protections |

The private runtime currently defines more than 50 structured tools. Tool availability is narrowed by request category so the model does not compete against the entire catalog on every turn.

## Voice and Agent Pipeline

- **Wake word:** Custom `Hey Persia` classifier with recorded five-fold cross-validation F1 of `0.927 +/- 0.072`
- **VAD:** Silero VAD with a rolling pre-buffer for capturing the beginning of speech
- **STT:** Faster-Whisper large-v3 with CUDA acceleration
- **LLM:** Fine-tuned Llama 3.1 8B Instruct model served locally through Ollama
- **Agent loop:** Structured tool calls, request-scoped tool routing, duplicate-call suppression, and a bounded multi-round ReAct loop
- **TTS:** Kokoro ONNX with sentence-level streaming and interruption handling
- **Interfaces:** Voice, Telegram, Slack, and a local FastAPI/WebSocket dashboard

## Safety and Reliability

Persia treats tool execution as an engineering boundary rather than allowing the model to directly control the operating system or external services.

- Destructive and outbound actions require explicit confirmation.
- File operations are restricted to configured allowed directories.
- Tool calls are validated against the available schemas before execution.
- Repeated successful calls and duplicate calls are suppressed by the agent loop.
- Unknown tool names are removed from assistant output instead of being spoken aloud.
- Memory facts are separated into core profile, recent recall, archival, and prospective reminder tiers.
- User-stated facts are preserved as authoritative; inferred facts do not silently overwrite them.
- Errors are returned to the loop so the assistant can report failures instead of claiming success.

## Evaluation Evidence

The project includes recorded evaluation work in the private development materials. The most concrete results currently documented are:

| Component | Result | Scope |
| --- | --- | --- |
| Wake-word classifier | F1 `0.927 +/- 0.072` | Five-fold cross-validation |
| PDF document pipeline | `13/13` automated tests passed | Digital PDFs, AcroForms, scanned and degraded inputs |
| PDF scan processing | Approximately `21 seconds/page` warm | Scanned form path on the development hardware |
| Fine-tuning dataset | `3,682` examples | Custom Persia examples plus converted tool-use examples |

These figures are project-level development results, not a claim of universal production performance. The repository deliberately does not publish private datasets, model weights, credentials, or personal runtime data.

## Public Repository Contents

```text
Speaking-AI/
├── browser-bridge/
│   ├── server.py                 Local FastAPI/WebSocket bridge
│   ├── extension/                Chrome Manifest V3 extension
│   ├── requirements.txt
│   └── test_*.py                 Bridge smoke tests
├── fine-tune/
│   ├── train.py                  QLoRA training entry point
│   ├── export_gguf.sh             Adapter merge and GGUF export workflow
│   └── scripts/                  Dataset conversion and assembly utilities
├── CAPABILITIES.md               Published capability map
├── run.sh                        Local launcher for the complete private checkout
└── .gitignore                    Exclusion rules for secrets and local artifacts
```

The following are intentionally not part of the public snapshot: `voice-agent/`, `.env` files, OAuth credentials, tokens, memory databases, virtual environments, model outputs, training datasets, personalized prompts, internal documentation, and presentation materials.

## Run the Published Browser Bridge

The browser bridge is a local FastAPI service that connects the assistant to a Chrome extension over WebSocket.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r browser-bridge/requirements.txt
python browser-bridge/server.py
```

The bridge listens on `127.0.0.1:8765`. Load `browser-bridge/extension/` as an unpacked Chrome extension, then use the bridge smoke tests after the extension is connected:

```bash
python browser-bridge/test_jobs.py
python browser-bridge/test_job_details.py
```

These tests require an active browser session and the target site to be available. They are integration smoke tests, not a fully offline test suite.

## Fine-Tuning Workflow

The published utilities describe the training workflow for a local Llama-based tool-calling model:

1. Prepare a private training and validation dataset that matches the production tool schemas.
2. Run `fine-tune/train.py` to train a QLoRA adapter.
3. Run `fine-tune/export_gguf.sh` to merge the adapter and export a GGUF model.
4. Register the model with Ollama and point the private runtime at the resulting model tag.

Training data, adapters, merged weights, and GGUF files are excluded because they are large, personalized, and not required to inspect the training code.

## Configuration and Privacy

Do not commit credentials or local runtime state. Configure integrations through environment variables or local configuration files that remain outside version control. This includes:

- Hugging Face, Telegram, Slack, Google, Apple, and other service credentials
- OAuth client files and refresh tokens
- Allowed local directory paths
- SQLite memory databases
- Browser session data and generated logs

Before publishing a clone of this project, inspect the staged file list and run a secret scanner. If a credential has ever been exposed, revoke it and issue a replacement even if the file was later ignored.

## Current Scope and Limitations

- The public snapshot is not a one-command installation of the complete voice assistant because the runtime and private configuration are excluded.
- External integrations require their own accounts, credentials, permissions, and service availability.
- Browser automation depends on DOM structures that can change without notice.
- OCR quality depends on scan resolution, document quality, and layout complexity.
- The evaluation results above are development measurements; broader held-out and production-scale evaluation remains future work.

## License and Ownership

Review ownership and licensing for any third-party datasets, base models, model conversions, and integration code before distributing a public release. Add a project license once the publication scope and dependency terms have been finalized.
