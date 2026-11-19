import json
from pathlib import Path

# Resolve paths relative to the repository root (one level above `src`)
base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
input_file = data_dir / "train_dataset.jsonl"
output_file = data_dir / "train_lora.jsonl"

# Ensure output directory exists
output_file.parent.mkdir(parents=True, exist_ok=True)

out = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)

        # 1) Extract question safely 
        if "extra" in row and "question" in row["extra"]:
            instruction = row["extra"]["question"]
        else:
            instruction = row.get("question", "")

        # 2) Extract gold answer safely 
        if "extra" in row and "gold_answer" in row["extra"]:
            gold = row["extra"]["gold_answer"]
        else:
            gold = row.get("gold_answer", "")

        #  3) Build dialogue
        dialogue = ""
        for turn in row.get("turns", []):
            role = "Student" if turn["role"] == "student" else "Tutor"
            dialogue += f"{role}: {turn['content']}\n"

        # 4) Build misconceptions 
        miscon = ""
        for m in row.get("misconceptions", []):
            miscon += f"- Misconception: {m['student_answer']}\n  Fix: {m['fix']}\n"

        # 5) Extract reasoning & hints 
        reasoning = "\n".join(row.get("extra", {}).get("reasoning", []))
        hints = "\n".join(row.get("extra", {}).get("hints", []))

        # 6) Build final output text 
        output = (
            f"Correct Answer: {gold}\n\n"
            f"Reasoning:\n{reasoning}\n\n"
            f"Dialogue:\n{dialogue}\n"
            f"Misconceptions:\n{miscon}\n"
            f"Hints:\n{hints}"
        )

        out.append({
            "instruction": instruction,
            "input": "",
            "output": output
        })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Saved LoRA dataset to:", output_file)
