"""Combine all JSONL datasets into train/val splits for fine-tuning."""
import json, pathlib, random

DATA = pathlib.Path(__file__).parent.parent / "data"
OUT  = pathlib.Path(__file__).parent.parent / "data"

PERSIA_FILES = [
    "cat01_file_tools.jsonl",
    "cat02_calendar_tools.jsonl",
    "cat03_gmail_tools.jsonl",
    "cat04_notes_tools.jsonl",
    "cat05_todo_tools.jsonl",
    "cat06_system_tools.jsonl",
    "cat07_browser_tools.jsonl",
    "cat08_chained_calls.jsonl",
    "cat09_confirmation_flows.jsonl",
    "cat10_identity_personality.jsonl",
    "cat11_refusals_boundaries.jsonl",
    "cat12_tool_errors.jsonl",
    "cat13_voice_behavior.jsonl",
    "cat14_clarification_flows.jsonl",
    "cat15_morning_briefing.jsonl",
    "cat16_context_carryover.jsonl",
]

GLAIVE_FILE = "glaive_converted.jsonl"

VAL_RATIO   = 0.05   # 5% held out for validation
RANDOM_SEED = 42


def load_jsonl(path: pathlib.Path) -> list[dict]:
    examples = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  WARN: {path.name}:{i} — {e}")
    return examples


def write_jsonl(path: pathlib.Path, examples: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main() -> None:
    rng = random.Random(RANDOM_SEED)

    # ── Load Persia examples ──────────────────────────────────────────────────
    persia = []
    for fname in PERSIA_FILES:
        p = DATA / fname
        if not p.exists():
            print(f"  MISSING: {fname}")
            continue
        batch = load_jsonl(p)
        print(f"  {len(batch):4d}  {fname}")
        persia.extend(batch)

    print(f"\nPersia total: {len(persia)}")

    # ── Load Glaive examples ──────────────────────────────────────────────────
    glaive_path = DATA / GLAIVE_FILE
    if glaive_path.exists():
        glaive = load_jsonl(glaive_path)
        print(f"Glaive total: {len(glaive)}")
    else:
        glaive = []
        print("  MISSING: glaive_converted.jsonl — training on Persia data only")

    # ── Combine and shuffle ───────────────────────────────────────────────────
    all_examples = persia + glaive
    rng.shuffle(all_examples)
    print(f"Combined:     {len(all_examples)}")

    # ── Split train / val ─────────────────────────────────────────────────────
    n_val   = max(1, int(len(all_examples) * VAL_RATIO))
    n_train = len(all_examples) - n_val

    val   = all_examples[:n_val]
    train = all_examples[n_val:]

    print(f"Train:        {n_train}")
    print(f"Val:          {n_val}")

    # ── Write splits ──────────────────────────────────────────────────────────
    train_path = OUT / "train.jsonl"
    val_path   = OUT / "val.jsonl"

    write_jsonl(train_path, train)
    write_jsonl(val_path, val)

    print(f"\nWrote {train_path}")
    print(f"Wrote {val_path}")


if __name__ == "__main__":
    main()
