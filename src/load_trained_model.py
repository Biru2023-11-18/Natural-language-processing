from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

#  1. Base model 
base_model = "Qwen/Qwen2.5-1.5B-Instruct"

#  2. Load base model
model = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype=torch.bfloat16,  # or torch.float16 if bfloat16 not supported
    device_map="auto"
)

#  3. Load LoRA adapter
lora_path = "qwen_lora_output/checkpoint-100"
model = PeftModel.from_pretrained(model, lora_path, local_files_only=True)
model.eval()

#  4. Load tokenizer 
tokenizer = AutoTokenizer.from_pretrained(base_model)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

#  5. Chat function using ChatML formatting 
def chat(prompt, max_new_tokens=200, temperature=0.7):
    chatml_prompt = f"<|im_start|>user\n{prompt}\n<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(chatml_prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            pad_token_id=tokenizer.pad_token_id
        )

    response = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    # Remove prompt part to keep only assistant reply
    reply = response.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0].strip()
    return reply

#  6. Interactive loop 
print("Chatbot is ready! Type 'exit' to quit.")
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = chat(user_input)
    print("Bot:", response)
