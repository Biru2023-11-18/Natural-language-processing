import os
import torch
import matplotlib.pyplot as plt
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    TrainerCallback,
)
from peft import LoraConfig, get_peft_model
from pathlib import Path

# Track training logs
training_loss_log = []
learning_rate_log = []
grad_norm_log = []

class LoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is None:
            return
        if "loss" in logs:
            training_loss_log.append((state.global_step, logs["loss"]))
        if "learning_rate" in logs:
            learning_rate_log.append((state.global_step, logs["learning_rate"]))
        if "grad_norm" in logs:
            grad_norm_log.append((state.global_step, logs["grad_norm"]))

# Load base model
model_name = "Qwen/Qwen2.5-1.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    load_in_4bit=True,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

# Load dataset
base_dir = Path(__file__).resolve().parent.parent
train_file = base_dir / "data/train_lora.jsonl"
if not train_file.exists():
    raise FileNotFoundError(f"Dataset missing: {train_file}")

dataset = load_dataset("json", data_files=str(train_file))
dataset = dataset["train"].train_test_split(test_size=0.05, shuffle=True, seed=42)

# Convert instruction rows into ChatML

def format_row(example):
    user_msg = example["instruction"]
    if example.get("input"):
        user_msg += "\n" + example["input"]

    assistant_msg = example["output"] + tokenizer.eos_token

    chatml = (
        "<|im_start|>user\n"
        f"{user_msg}\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{assistant_msg}\n"
        "<|im_end|>"
    )

    return {"text": chatml}

formatted = dataset.map(format_row)

# Tokenize examples
max_length = 2048

def tokenize(batch):
    tokens = tokenizer(
        batch["text"],
        truncation=True,
        max_length=max_length,
        padding=False,
    )

    labels = []
    for seq in tokens["input_ids"]:
        labels.append([tok if tok != tokenizer.pad_token_id else -100 for tok in seq])

    tokens["labels"] = labels
    return tokens

data = formatted.map(tokenize, batched=True, remove_columns=formatted["train"].column_names)

# Standard LM collator
collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# LoRA configuration
lora_cfg = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)

model = get_peft_model(model, lora_cfg)
model.print_trainable_parameters()

# Diagnostics: check trainable parameters after LoRA wrap
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Model params: {trainable_params} trainable out of {total_params} total")
if trainable_params == 0:
    print("Warning: no trainable parameters detected. Forcing LoRA params to require grad if present.")
    for n, p in model.named_parameters():
        if "lora" in n.lower() or "adapter" in n.lower():
            p.requires_grad = True
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"After forcing: {trainable_params} trainable out of {total_params} total")
    
# Ensure caching and gradient checkpointing settings won't break backprop
try:
    model.config.use_cache = False
except Exception:
    pass
try:
    if hasattr(model, 'gradient_checkpointing_disable'):
        model.gradient_checkpointing_disable()
except Exception:
    pass

# Training arguments
training_args = TrainingArguments(
    output_dir="qwen2_lora_output",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=8e-5,
    warmup_steps=100,
    max_steps=200,
    bf16=True,
    logging_steps=1,
    save_steps=200,
    eval_steps=200,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    report_to="none",
)

# Trainer setup
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=data["train"],
    eval_dataset=data["test"],
    data_collator=collator,
    callbacks=[LoggingCallback()],
)

# Train and save adapter
try:
    trainer.train()
except KeyboardInterrupt:
    print("Training interrupted")
finally:
    os.makedirs("qwen2_lora_output", exist_ok=True)
    model.save_pretrained("qwen2_lora_adapter")
    tokenizer.save_pretrained("qwen2_lora_adapter")
    print("Saved LoRA adapter.")

# Plot metrics
if training_loss_log:
    steps, loss = zip(*training_loss_log)
    plt.plot(steps, loss)
    plt.title("Training Loss")
    plt.xlabel("Step")
    plt.ylabel("Loss")
    plt.grid(True)
    plt.savefig("qwen2_lora_output/loss.png", dpi=300)
    plt.close()

if learning_rate_log:
    s, lr = zip(*learning_rate_log)
    plt.plot(s, lr)
    plt.title("Learning Rate")
    plt.xlabel("Step")
    plt.ylabel("LR")
    plt.grid(True)
    plt.savefig("qwen2_lora_output/lr.png", dpi=300)
    plt.close()

if grad_norm_log:
    s, g = zip(*grad_norm_log)
    plt.plot(s, g)
    plt.title("Gradient Norm")
    plt.xlabel("Step")
    plt.ylabel("Grad Norm")
    plt.grid(True)
    plt.savefig("qwen2_lora_output/gradnorm.png", dpi=300)
    plt.close()

print("All done. Metrics saved.")