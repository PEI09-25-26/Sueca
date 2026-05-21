from dataclasses import dataclass, asdict


@dataclass
class CardDetection:
    rank: str
    suit: str
    confidence: float

    def to_json(self) -> dict:
        return asdict(self)
