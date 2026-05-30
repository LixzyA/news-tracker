from enum import Enum
from pydantic import BaseModel, field_validator

class NewsSource(Enum):
    CNBC = "cnbc-news"
    CNN = "cnn-news"
    REPUBLIKA = "republika-news"

class ClassifiedNews(BaseModel):
    model_config = {"extra": "forbid"}

    is_highly_impactful: bool
    reasoning: str
    confidence: float

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {v}")
        return v