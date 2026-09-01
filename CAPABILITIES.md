# Persia — Capability Map

**Last updated:** 2026-06-19

---

## Core Voice Pipeline

| Component | Details |
|---|---|
| Wake word | "Hey Persia" — custom-trained model (F1=0.927), runs locally at 80ms chunks |
| VAD | Silero VAD, fully offline, no API required |
| Speech-to-text | Faster-Whisper large-v3 on CUDA |
| Interruption | Persia stops mid-sentence when you speak; 2-second pre-buffer catches the start of your words |
| Text-to-speech | Kokoro TTS (ONNX), number normalization ($12,000 → "twelve thousand"), no artifacts |
| LLM | `persia-f16:latest` in Ollama — Meta-Llama-3.1-8B, QLoRA fine-tune, 1304 Persia examples + 2378 Glaive |
| Agentic loop | ReAct pattern — calls multiple tools in sequence per turn, with a planning step for multi-step requests |

---

## Tools (58 total)

### File System
| Tool | Description |
|---|---|
| `list_directory` | List contents of a directory |
| `read_file` | Read a file with optional offset/limit |
| `write_file` | Write a new file |
| `edit_file` | In-place replace within an existing file |
| `delete_file` | Delete a file (verbal confirmation required) |
| `search_files` | Walk directory tree, match by filename or content |
| `glob_files` | Pattern-match files |
| `grep_files` | Regex search with context lines |

### Calendar
Apple CalDAV + Google Calendar API v3 run simultaneously. Events are labeled [Apple] or [Google].

| Tool | Description |
|---|---|
| `get_calendar_events` | Fetch events from both Apple and Google calendars |
| `create_calendar_event` | Create event with recurrence support (verbal confirmation required) |
| `update_calendar_event` | Edit an existing event |
| `delete_calendar_event` | Delete an event (verbal confirmation required) |

### Gmail
| Tool | Description |
|---|---|
| `read_emails` | Fetch email list — must call first to get IDs |
| `read_email_body` | Get full body of a specific email |
| `send_email` | Send a new email (verbal confirmation required) |
| `reply_to_email` | Reply to an email (verbal confirmation required) |
| `forward_email` | Forward an email |
| `search_emails` | Search by query |
| `trash_email` | Move a specific email to trash |
| `trash_email_by_query` | Trash emails matching a search query |

### Notes (Obsidian)
Stored as `.md` files with YAML frontmatter in `Obsidian Vault/Persia/`.

| Tool | Description |
|---|---|
| `list_notes` | List all notes |
| `create_note` | Create a new note |
| `read_note` | Read a note's contents |
| `update_note` | Update an existing note |
| `delete_note` | Delete a note (verbal confirmation required) |

### Todos (Obsidian)
Stored as JSON in the Obsidian vault. Supports named lists (Shopping, Work, etc.).

| Tool | Description |
|---|---|
| `list_todos` | List todos, optionally filtered by list name |
| `add_todo` | Add a todo to a named list |
| `complete_todo` | Mark a todo as done |
| `delete_todo` | Delete a todo (verbal confirmation required) |

### Google Tasks
| Tool | Description |
|---|---|
| `list_task_lists` | List all Google Task lists |
| `list_tasks` | List tasks in a specific list |
| `create_task_list` | Create a new task list |
| `create_task` | Add a task with optional natural language due date |
| `complete_task` | Mark a task complete |
| `update_task` | Edit a task's title, notes, or due date |
| `delete_task` | Delete a task (verbal confirmation required) |

### Slack
| Tool | Description |
|---|---|
| `list_slack_channels` | List available channels |
| `read_slack_channel` | Read messages from a channel |
| `read_slack_thread` | Read a specific thread |
| `search_slack` | Search Slack messages |
| `get_slack_dm_history` | Fetch DM history with a user |
| `post_slack_message` | Post a message to a channel |
| `reply_to_slack_thread` | Reply to an existing thread |

### Memory
SQLite backend with FTS5 keyword search + vector search (sentence-transformers), hybrid Reciprocal Rank Fusion retrieval. Facts extracted by Ollama in a background thread after every turn.

| Tool | Description |
|---|---|
| `remember_fact` | Store a fact permanently |
| `forget_fact` | Mark a fact as dormant |
| `recall_about` | Retrieve facts related to a topic |
| `add_reminder` | Add a prospective/future reminder |
| `correct_fact` | Correct a previously stored fact |
| `recall_sessions` | Retrieve past session summaries |

**Memory tiers:**
- **Core Profile** — ~3KB, always in context, rebuilt daily
- **Recall** — last 7 days, FTS5 keyword search
- **Archival** — unlimited history, hybrid vector + keyword
- **Prospective** — future reminders and trigger-based recalls

**Key rules:** User-stated facts are immutable — Persia's inferences never override what you told her directly. Facts never hard-deleted — they become dormant and are always recoverable.

### Browser / LinkedIn
Chrome extension bridge (Manifest V3) + FastAPI+WebSocket server.

| Tool | Description |
|---|---|
| `browser_query` | Query LinkedIn inbox, jobs, profiles via DOM extractors |

### Documents (PDF)
Stack: PyMuPDF + pdf2image + EasyOCR + OpenCV + LayoutLMv3. 13/13 tests pass.

| Tool | Description |
|---|---|
| `read_document` | Extract text content from a PDF |
| `list_form_fields` | Detect fillable fields in a PDF form |
| `fill_document` | Fill a PDF form and save the output |

### System
| Tool | Description |
|---|---|
| `run_command` | Execute a shell command (blocklist enforced) |
| `glob_files` | Pattern-match files (also listed under File System) |
| `grep_files` | Regex file search (also listed under File System) |

---

## Safety & Confirmation

Verbal confirmation is required before any destructive or send action. Persia reads back the full details and waits for a spoken "yes" or "no" before executing.

**Tools requiring confirmation:** `delete_file`, `create_calendar_event`, `delete_calendar_event`, `delete_note`, `delete_todo`, `delete_task`, `send_email`, `reply_to_email`

---

## Interfaces

| Interface | Details |
|---|---|
| **Voice** | Primary — always-on via wake word |
| **Telegram bot** | Text in/out, voice notes (OGG→STT), inline Yes/No buttons for confirmations, commands: `/sleep` `/status` `/clear` `/wakeword on\|off` `/help` |
| **Web UI** | `localhost:8766` — 3-tab dark interface: LIVE (transcript + context), SESSIONS (log grouped by date), MEMORY BROWSER (filterable fact table + D3 force graph) |

---

## Pending / Not Yet Built

| Item | Status | Notes |
|---|---|---|
| Google Jobs search | Research complete, build not started | `GOOGLE_JOBS_INTEGRATION.md` — SerpApi via HTTP, code drafted, 2–4 hrs to wire in |
| Apple Reminders | Planned | CalDAV VTODO — iOS 13+ compatibility not confirmed |
| Browser Phase 7 | Planned | `<all_urls>` extension permission + Indeed extractor |
| Web search | Backlog | Local SearXNG or DuckDuckGo API |
| Web fetch | Backlog | `fetch_url` via httpx — no Chromium required |
| Computer use | Backlog | Full GUI automation — screenshot, click, type, scroll |
