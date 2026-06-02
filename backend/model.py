from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator

class NewsSource(Enum):
    CNBC = "cnbc-news"
    CNN = "cnn-news"
    REPUBLIKA = "republika-news"

class ClassifiedNews(BaseModel):
    model_config = {"extra": "forbid"}

    is_high_impact: bool
    confidence: float
    # Optional fields with sane defaults so partial responses still validate
    sentiment: str = "neutral"
    impact_category: str = "none"
    affected_sectors: list[str] = []
    reason: str = ""

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {v}")
        return v

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str) -> str:
        valid_sentiments = {"positive", "negative", "neutral", "mixed"}
        if v not in valid_sentiments:
            raise ValueError(f"Sentiment must be one of {valid_sentiments}, got '{v}'")
        return v

    @field_validator("impact_category")
    @classmethod
    def validate_impact_category(cls, v: str) -> str:
        valid_categories = {"macro", "commodity", "regulatory", "corporate", "global", "political", "none"}
        if v not in valid_categories:
            raise ValueError(f"Impact category must be one of {valid_categories}, got '{v}'")
        return v

    @field_validator("affected_sectors")
    @classmethod
    def validate_affected_sectors(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            raise ValueError(f"Affected sectors must be a list of strings, got {type(v).__name__}")
        valid_sectors = {"Financials", "Energy", "Basic Materials", "Industrials", "Consumer Non-Cyclicals", "Consumer Cyclicals", "Healthcare", "Properties & Real Estate", "Technology", "Infrastructure", "Transportation & Logistics"}
        for sector in v:
            if not isinstance(sector, str):
                raise ValueError(f"Each affected sector must be a string, got {type(sector).__name__} in list")
            if sector not in valid_sectors:
                raise ValueError(f"Affected sector must be one of {valid_sectors}, got '{sector}'")
        return v

class SubscribeRequest(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    status: str
    message: str
