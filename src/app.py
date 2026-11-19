import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import torch

# Load Model 
base_model = "Qwen/Qwen2.5-1.5B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
)

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    base_model,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.float16,
)

# Load LoRA adapter
lora_path = "qwen_lora_adapter"
print(f"Loading LoRA from {lora_path}...")
model = PeftModel.from_pretrained(model, lora_path)
model.eval() 


tokenizer = AutoTokenizer.from_pretrained(base_model)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

print("Warming up model (first inference is slowest)...")
warmup_prompt = "<|im_start|>user\nHello<|im_end|>\n<|im_start|>assistant\n"
inputs = tokenizer(warmup_prompt, return_tensors="pt").to(model.device)
with torch.no_grad():
    _ = model.generate(**inputs, max_new_tokens=5, do_sample=False)
print("✅ Model warmed up!")


def chat_single_turn(prompt, max_new_tokens=1000, temperature=0.7):
    prompt_text = f"{prompt}\nPlease answer in detail.\n"
    
    chatml_prompt = (
        f"<|im_start|>user\n{prompt_text}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    inputs = tokenizer(chatml_prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            do_sample=True,
            eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>"),
            pad_token_id=tokenizer.pad_token_id,
        )

    text = tokenizer.decode(output[0], skip_special_tokens=True)

    # Extract only assistant reply
    if "<|im_start|>assistant" in text:
        text = text.split("<|im_start|>assistant")[-1]
    if "<|im_end|>" in text:
        text = text.split("<|im_end|>")[0]

    # Remove remnants of user input
    text = text.replace(prompt, "").strip()
    return text

# ----------------- Respond function -----------------
def respond(message, history):
    reply = chat_single_turn(message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply}
    ]
    return history

# ----------------- Gradio UI (Gradio 6.0+ Compatible)
with gr.Blocks() as demo:

    gr.HTML("""
    <style>
    .chat-container {
        max-width: 1400px !important;
        margin: auto;
        width: 100%;
    }
    .gradio-container .gr-chatbot {
        width: 100% !important;
    }
    .gr-textbox textarea {
        font-size: 16px;
    }
    </style>
    """)

    gr.Markdown("<h2 style='text-align:center;'>🧪 Your Science Tutor</h2>")

    chatbot = gr.Chatbot(
        elem_classes="chat-container",
        height=700,
        show_label=False
    )
    msg = gr.Textbox(
        placeholder="Ask something...",
        lines=3,
        container=False,
        show_label=False
    )

    msg.submit(respond, [msg, chatbot], chatbot)

# Launch the app
demo.launch(server_name="0.0.0.0", server_port=7860)