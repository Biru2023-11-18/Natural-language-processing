import argparse
import json
import os
import random
import re
from pathlib import Path
from typing import Dict, List

from schemas import Sample, Misconception, Quality
from llm import LLMClient

ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT / "prompts"


def read_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


def first_json_blob(text: str) -> Dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response.")
    return json.loads(match.group(0))


def build_creator_messages(prompt: str, meta: Dict) -> List[Dict[str, str]]:
    user_msg = {
        "role": "user",
        "content": json.dumps(meta, ensure_ascii=False),
    }
    return [{"role": "system", "content": prompt}, user_msg]


def build_misconception_messages(prompt: str, question: str, gold_answer: str) -> List[Dict[str, str]]:
    payload = {"question": question, "gold_answer": gold_answer}
    return [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def build_critic_messages(prompt: str, sample: Dict) -> List[Dict[str, str]]:
    return [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(sample, ensure_ascii=False)}]


def synthesize_sample(meta: Dict, client: LLMClient, prompts: Dict[str, str]) -> Sample:
    creator_resp = client.chat(build_creator_messages(prompts["creator"], meta), max_tokens=900)
    creator_json = first_json_blob(creator_resp)

    misconceptions: List[Misconception] = []
    for m in creator_json.get("misconceptions", []):
        misconceptions.append(Misconception(type=m.get("type", "unspecified"), student_answer=m.get("student_answer", ""), fix=m.get("fix", "")))

    # Expand with extra misconceptions via dedicated agent
    extra_resp = client.chat(
        build_misconception_messages(prompts["misconception"], creator_json.get("question", ""), creator_json.get("gold_answer", "")),
        max_tokens=400,
    )
    try:
        extra_json = first_json_blob(extra_resp)
        for m in extra_json.get("misconceptions", []):
            misconceptions.append(Misconception(type=m.get("type", "unspecified"), student_answer=m.get("student_answer", ""), fix=m.get("fix", "")))
    except Exception:
        pass  # keep creator misconceptions only if parsing fails

    # Critic evaluates the combined sample
    critic_payload = {
        "question": creator_json.get("question", ""),
        "gold_answer": creator_json.get("gold_answer", ""),
        "reasoning": creator_json.get("reasoning", []),
        "hints": creator_json.get("hints", []),
        "tutor_student_dialogue": creator_json.get("tutor_student_dialogue", []),
        "misconceptions": [m.__dict__ for m in misconceptions],
        "meta": meta,
    }
    critic_resp = client.chat(build_critic_messages(prompts["critic"], critic_payload), max_tokens=200)
    try:
        critic_json = first_json_blob(critic_resp)
        quality = Quality(critic_score=float(critic_json.get("score", 0.0)), passed=bool(critic_json.get("passed", False)), notes=critic_json.get("notes"))
    except Exception:
        quality = Quality(critic_score=0.0, passed=False, notes="critic parsing failed")

    turns = []
    for turn in creator_json.get("tutor_student_dialogue", []):
        if "role" in turn and "content" in turn:
            turns.append({"role": turn["role"], "content": turn["content"]})

    sample = Sample(
        subject=meta["subject"],
        level=meta["level"],
        topic=meta["topic"],
        difficulty=meta["difficulty"],
        cognitive_dim=meta["cognitive_dim"],
        item_type=meta["item_type"],
        scenario=meta["scenario"],
        question=creator_json.get("question", ""),
        gold_answer=creator_json.get("gold_answer", ""),
        turns=turns,
        misconceptions=misconceptions,
        quality=quality,
        extra={
            "reasoning": creator_json.get("reasoning", []),
            "hints": creator_json.get("hints", []),
        },
    )
    return sample


def random_difficulty() -> str:
    return random.choice(["easy", "medium", "hard"])


def random_cognitive_dim() -> str:
    return random.choice(["concept", "compute", "experiment", "transfer"])


def random_item_type() -> str:
    return random.choice(["free_response", "multiple_choice", "experiment_design"])


def random_scenario() -> str:
    return random.choice(["classroom", "self_study", "exam_prep"])


def main():
    parser = argparse.ArgumentParser(description="Generate Science Tutor Q&A synthetic data.")
    parser.add_argument("--subject", choices=["physics", "biology", "chemistry"], required=True)
    parser.add_argument("--level", choices=["middle_school", "high_school", "intro_college"], required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--count", type=int, default=1, help="Number of samples to generate.")
    parser.add_argument("--out", type=Path, default=Path("data/sample.jsonl"))
    args = parser.parse_args()

    prompts = {
        "creator": read_prompt("creator.md"),
        "critic": read_prompt("critic.md"),
        "misconception": read_prompt("misconception.md"),
    }

    client = LLMClient()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("w", encoding="utf-8") as f:
        completed = 0
        for i in range(args.count):
            meta = {
                "subject": args.subject,
                "level": args.level,
                "topic": args.topic,
                "difficulty": random_difficulty(),
                "cognitive_dim": random_cognitive_dim(),
                "item_type": random_item_type(),
                "scenario": random_scenario(),
            }

            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    sample = synthesize_sample(meta, client, prompts)
                    f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
                    completed += 1
                    print(
                        f"[{completed}/{args.count}] wrote sample (try {attempts}) "
                        f"difficulty={sample.difficulty}, score={sample.quality.critic_score:.2f}, passed={sample.quality.passed}"
                    )
                    break
                except Exception as exc:
                    if attempts >= 3:
                        print(f"[{completed}/{args.count}] failed after {attempts} attempts: {exc}")
                    else:
                        print(f"Retrying ({attempts}/3) after error: {exc}")


if __name__ == "__main__":
    main()
