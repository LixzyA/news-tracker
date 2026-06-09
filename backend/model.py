from enum import StrEnum
from pydantic import BaseModel, field_validator, Field

class NewsSource(StrEnum):
    CNBC = "cnbc-news"
    CNN = "cnn-news"
    REPUBLIKA = "republika-news"

class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ImpactCategory(StrEnum):
    MACRO = "macro"
    COMMODITY = "commodity"
    REGULATORY = "regulatory"
    CORPORATE = "corporate"
    GLOBAL = "global"
    POLITICAL = "political"
    NONE = "none"

class AffectedSector(StrEnum):
    FINANCIALS = "financials"
    ENERGY = "energy"
    BASIC_MATERIALS = "basic materials"
    INDUSTRIALS = "industrials"
    CONSUMER_NON_CYCLICALS = "consumer non-cyclicals"
    CONSUMER_CYCLICALS = "consumer cyclicals"
    HEALTHCARE = "healthcare"
    PROPERTIES_REAL_ESTATE = "properties & real estate"
    TECHNOLOGY = "technology"
    INFRASTRUCTURE = "infrastructure"
    TRANSPORTATION_LOGISTICS = "transportation & logistics"

#TODO: add impact_magnitude
class ClassifiedNews(BaseModel):

    is_high_impact: bool
    confidence: float = Field(description="""
How confident you are in your own classification of this news. Reflects the clarity and unambiguity of the available information, not the magnitude of market impact.
- 0.9–1.0: The news is explicit and unambiguous — classification is near-certain.
- 0.7–0.9: Clear signal with minor interpretive uncertainty.
- 0.5–0.7: Some ambiguity in the text or its market implications.
- 0.3–0.5: LSignificant uncertainty — the news is vague, incomplete, or context-dependent.
- 0.0–0.3: Highly uncertain — insufficient information to classify reliably.
""")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description="""Market sentiment from the perspective of IDX impact.
Sentiment definitions (from the perspective of IDX market impact):
- positive: likely to increase investor confidence, stock prices, or capital inflows
- negative: likely to decrease investor confidence, cause sell-offs, or capital outflows
- neutral: informational only, no directional market bias
- mixed: contains both positive and negative signals for different sectors (e.g. weak rupiah hurts importers but helps exporters)                                
""")
    impact_category: ImpactCategory = Field(default=ImpactCategory.NONE)
    affected_sectors: list[AffectedSector] = Field(default=[], description="List of sectors affected by the news")
    reason: str

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {v}")
        return v

class MessageResponse(BaseModel):
    status: str
    message: str
