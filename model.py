from dataclasses import dataclass
from datetime import date
from enum import Enum
from pydantic import BaseModel


class NewsSource(Enum):
    CNBC = "cnbc-news"
    CNN = "cnn-indonesia"
    BBC = "bbc-news"


@dataclass
class News:
    title: str
    date: date
    content_snippet: str
    url: str
    image_url: str
    source: NewsSource

class ClassifiedNews(BaseModel):
    is_highly_impactful: bool
    reasoning: str
    confidence: float
