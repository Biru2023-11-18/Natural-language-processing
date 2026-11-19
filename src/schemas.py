from dataclasses import asdict, dataclass, field
from typing import List, Literal, Optional, Dict, Any

Subject = Literal["physics", "biology", "chemistry"]
Level = Literal["middle_school", "high_school", "intro_college"]
Difficulty = Literal["easy", "medium", "hard"]
CognitiveDim = Literal["concept", "compute", "experiment", "transfer"]
ItemType = Literal["multiple_choice", "free_response", "experiment_design"]
Scenario = Literal["classroom", "self_study", "exam_prep"]


@dataclass
class Misconception:
    type: str
    student_answer: str
    fix: str


@dataclass
class Quality:
    critic_score: float
    passed: bool
    notes: Optional[str] = None


@dataclass
class Sample:
    subject: Subject
    level: Level
    topic: str
    difficulty: Difficulty
    cognitive_dim: CognitiveDim
    item_type: ItemType
    scenario: Scenario
    question: str
    gold_answer: str
    turns: List[Dict[str, str]]
    misconceptions: List[Misconception] = field(default_factory=list)
    quality: Optional[Quality] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["misconceptions"] = [asdict(m) for m in self.misconceptions]
        data["quality"] = asdict(self.quality) if self.quality else None
        return data
