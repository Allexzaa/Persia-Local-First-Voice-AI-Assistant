"""
convert_glaive.py

Converts glaive-function-calling-v2 dataset to Llama-3.2 chat template format
for use as training data alongside custom Persia examples.

Glaive format:
  system: "SYSTEM: You are a helpful assistant with access to..."
  chat:   "USER: ...\n\nA: ...<|endoftext|>\n\nUSER: ...\n\nFUNCTION RESPONSE: ...\n\nA: ..."

Output format (Llama-3.2 instruct chat template):
  [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "tool",      "content": "..."},   # function response
    {"role": "assistant", "content": "..."},
  ]

Saved as JSONL: one JSON object per line with key "messages".
"""

import json
import re
import sys
from pathlib import Path

from datasets import load_dataset

# --- Config ---
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "glaive_converted.jsonl"
MAX_EXAMPLES = 5000       # cap — we only need a fraction of the 112k dataset
MIN_TURNS    = 2          # skip single-turn examples (not useful for tool calling)
TOOL_CALL_ONLY = True     # if True, only keep examples that contain a function call


def clean_system(text: str) -> str:
    """Strip the leading 'SYSTEM: ' prefix glaive adds."""
    return re.sub(r'^SYSTEM:\s*', '', text.strip())


def parse_chat(chat: str) -> list[dict]:
    """
    Parse glaive chat string into a list of {role, content} dicts.
    Roles in glaive: USER, ASSISTANT, FUNCTION RESPONSE
    Separator: triple newline between turns.
    """
    messages = []

    parts = re.split(r'\n{2,}', chat.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part.startswith("USER:"):
            content = part[len("USER:"):].strip()
            messages.append({"role": "user", "content": content})

        elif part.startswith("FUNCTION RESPONSE:"):
            content = part[len("FUNCTION RESPONSE:"):].strip()
            messages.append({"role": "tool", "content": content})

        elif part.startswith("ASSISTANT:"):
            content = part[len("ASSISTANT:"):].strip()
            content = content.replace("<|endoftext|>", "").strip()
            content = normalise_function_call(content)
            messages.append({"role": "assistant", "content": content})

    return messages


def normalise_function_call(text: str) -> str:
    """
    Glaive uses: <functioncall> {"name": "...", "arguments": '...'}
    Llama-3.2 tool calling uses a JSON block. We keep it as a readable
    assistant message with a clean JSON tool_call block.
    """
    match = re.search(r'<functioncall>\s*(\{.*\})', text, re.DOTALL)
    if not match:
        return text

    raw = match.group(1).strip()
    try:
        obj = json.loads(raw)
        # arguments may be a JSON string — parse it
        if isinstance(obj.get("arguments"), str):
            try:
                obj["arguments"] = json.loads(obj["arguments"])
            except json.JSONDecodeError:
                pass
        tool_call_str = json.dumps({"tool_call": obj}, ensure_ascii=False)
        # Replace the <functioncall> block with clean JSON
        return text[:match.start()].strip() + "\n" + tool_call_str if text[:match.start()].strip() else tool_call_str
    except json.JSONDecodeError:
        return text


def has_tool_call(messages: list[dict]) -> bool:
    return any("tool_call" in m["content"] for m in messages if m["role"] == "assistant")


def convert(max_examples: int = MAX_EXAMPLES) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading glaive-function-calling-v2...")
    ds = load_dataset("glaiveai/glaive-function-calling-v2", split="train")
    print(f"Total examples: {len(ds)}")

    written = 0
    skipped_short = 0
    skipped_no_tool = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for ex in ds:
            if written >= max_examples:
                break

            system_text = clean_system(ex["system"])
            messages = parse_chat(ex["chat"])

            if not messages:
                continue

            # Filter: skip examples with no tool calls if TOOL_CALL_ONLY
            if TOOL_CALL_ONLY and not has_tool_call(messages):
                skipped_no_tool += 1
                continue

            # Filter: skip too-short conversations
            if len(messages) < MIN_TURNS:
                skipped_short += 1
                continue

            # Build final message list with system prompt first
            full_messages = [{"role": "system", "content": system_text}] + messages

            f.write(json.dumps({"messages": full_messages}, ensure_ascii=False) + "\n")
            written += 1

    print(f"\nDone.")
    print(f"  Written:          {written}")
    print(f"  Skipped (short):  {skipped_short}")
    print(f"  Skipped (no tool):{skipped_no_tool}")
    print(f"  Output:           {OUTPUT_PATH}")


if __name__ == "__main__":
    max_ex = int(sys.argv[1]) if len(sys.argv) > 1 else MAX_EXAMPLES
    convert(max_ex)
