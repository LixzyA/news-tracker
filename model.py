from enum import Enum
from pydantic import BaseModel

class NewsSource(Enum):
    CNBC = "cnbc-news"
    CNN = "cnn-news"
    REPUBLIKA = "republika-news"

class ClassifiedNews(BaseModel):
    is_highly_impactful: bool
    reasoning: str
    confidence: float