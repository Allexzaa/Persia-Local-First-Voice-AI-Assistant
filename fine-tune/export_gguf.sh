#!/usr/bin/env bash
# Merge LoRA adapter into full model, then convert to GGUF Q4_K_M.
# Run from the fine-tune directory after training completes.
set -e

BASE_MODEL="unsloth/Meta-Llama-3.1-8B-Instruct"
ADAPTER_DIR="output/persia-lora/final"
MERGED_DIR="output/persia-merged"
GGUF_DIR="output/persia-gguf"
LLAMA_CPP="${HOME}/Dev-app/llama.cpp"   # adjust if your llama.cpp lives elsewhere

# ── Step 1: merge adapter into full weights ───────────────────────────────────
echo "==> Merging LoRA adapter into full model..."
source .venv/bin/activate
python3 - <<'PYEOF'
import pathlib, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL  = "unsloth/Meta-Llama-3.1-8B-Instruct"
ADAPTER_DIR = "output/persia-lora/final"
MERGED_DIR  = "output/persia-merged"

print(f"Loading base model: {BASE_MODEL}")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR, trust_remote_code=True)

print(f"Loading adapter: {ADAPTER_DIR}")
model = PeftModel.from_pretrained(model, ADAPTER_DIR)
model = model.merge_and_unload()

print(f"Saving merged model to: {MERGED_DIR}")
pathlib.Path(MERGED_DIR).mkdir(parents=True, exist_ok=True)
model.save_pretrained(MERGED_DIR)
tokenizer.save_pretrained(MERGED_DIR)
print("Merge complete.")
PYEOF

# ── Step 2: convert to GGUF ──────────────────────────────────────────────────
echo "==> Converting to GGUF..."
mkdir -p "$GGUF_DIR"
python3 "${LLAMA_CPP}/convert_hf_to_gguf.py" \
    "$MERGED_DIR" \
    --outfile "${GGUF_DIR}/persia-f16.gguf" \
    --outtype f16

# ── Step 3: quantize to Q4_K_M ───────────────────────────────────────────────
echo "==> Quantizing to Q4_K_M..."
"${LLAMA_CPP}/build/bin/llama-quantize" \
    "${GGUF_DIR}/persia-f16.gguf" \
    "${GGUF_DIR}/persia-q4_k_m.gguf" \
    Q4_K_M

echo ""
echo "Done! GGUF files in ${GGUF_DIR}:"
ls -lh "${GGUF_DIR}"/*.gguf
