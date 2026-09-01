"""Fine-tune Llama-3.1-8B-Instruct → Persia via QLoRA."""
import pathlib, torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

BASE_MODEL  = "unsloth/Meta-Llama-3.1-8B-Instruct"
DATA_DIR    = pathlib.Path(__file__).parent / "data"
OUTPUT_DIR  = pathlib.Path(__file__).parent / "output" / "persia-lora"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Tokenizer ─────────────────────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token    = tokenizer.eos_token
tokenizer.padding_side = "right"

# ── 4-bit quantization ────────────────────────────────────────────────────────
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# ── Base model ────────────────────────────────────────────────────────────────
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False

# ── LoRA config ───────────────────────────────────────────────────────────────
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# ── Datasets ──────────────────────────────────────────────────────────────────
def format_messages(example):
    return {"text": tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )}

train_ds = load_dataset("json", data_files=str(DATA_DIR / "train.jsonl"), split="train")
val_ds   = load_dataset("json", data_files=str(DATA_DIR / "val.jsonl"),   split="train")
train_ds = train_ds.map(format_messages, num_proc=4)
val_ds   = val_ds.map(format_messages,   num_proc=4)

# ── Training config ───────────────────────────────────────────────────────────
sft_config = SFTConfig(
    output_dir=str(OUTPUT_DIR),
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,          # effective batch = 16
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=50,
    weight_decay=0.01,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_grad_norm=1.0,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=200,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    max_length=2048,
    dataset_text_field="text",
    packing=True,
    report_to="none",
    seed=42,
)

# ── Trainer ───────────────────────────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    args=sft_config,
    peft_config=lora_config,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    processing_class=tokenizer,
)

print(f"Trainable parameters: "
      f"{sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
print(f"Train examples: {len(train_ds)}")
print(f"Val examples:   {len(val_ds)}")
print(f"Output dir:     {OUTPUT_DIR}")

trainer.train()

# ── Save final adapter ────────────────────────────────────────────────────────
final_dir = OUTPUT_DIR / "final"
trainer.save_model(str(final_dir))
tokenizer.save_pretrained(str(final_dir))
print(f"\nAdapter saved to {final_dir}")
