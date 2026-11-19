import glob
import json
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
output_file = data_dir / "train_dataset.jsonl"

input_files = [
    f for f in glob.glob(str(data_dir / "*.jsonl"))
    if Path(f).resolve() != output_file.resolve()
]

print("Merging files (excluding output):")
for f in input_files:
    print(" -", f)

output_file.parent.mkdir(parents=True, exist_ok=True)

# ---- Deduplication set ----
seen = set()

with open(output_file, "w", encoding="utf-8") as outfile:
    for filename in input_files:
        with open(filename, "r", encoding="utf-8") as infile:
            for line in infile:
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    print("Skipping invalid JSON:", line)
                    continue

                # Deduplicate entries using a stable hash
                key = json.dumps(obj, sort_keys=True)

                if key in seen:
                    continue  

                seen.add(key)
                outfile.write(json.dumps(obj, ensure_ascii=False) + "\n")

print(f"\nMerged dataset written to: {output_file}")
print(f"Total unique records: {len(seen)}")
