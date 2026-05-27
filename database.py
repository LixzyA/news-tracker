from sqlalchemy import Boolean, Float, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapped_column, Mapped, Session, relationship
from sqlalchemy.types import Date, Integer
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
TABLE_NAME = os.getenv("TABLE_NAME")
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}", 
                       pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW, pool_timeout=POOL_TIMEOUT, pool_recycle=POOL_RECYCLE)
Base = declarative_base()

class News(Base):
    __tablename__ = "news"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    content_snippet: Mapped[str] = mapped_column(String(), nullable=False)
    link: Mapped[str] = mapped_column(String(), nullable=False)
    image_url: Mapped[str] = mapped_column(String(), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    classified_data: Mapped["ClassifiedNews"] = relationship(back_populates="news")

class ClassifiedNews(Base):
    __tablename__ = "classified_news"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey("news.id"), nullable=False)
    is_impactful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(), nullable=True)
    news: Mapped["News"] = relationship(back_populates="classified_data")

Base.metadata.create_all(engine)


def query_news(link: str) -> News | None:
    with Session(engine) as session:
        news_list = session.query(News).where(News.link == link).first()
        if news_list:
            return news_list
    return None

def insert_news(news: dict, source: str, classified_data: dict):
    with Session(engine) as session:
        try:
            print(type(classified_data))
            classified_info = ClassifiedNews(
                is_impactful= classified_data["is_highly_impactful"],
                confidence= classified_data["confidence"],
                reason= classified_data["reasoning"]
            )

            new_article = News(
                title=news["title"],
                date=datetime.datetime.fromisoformat(news["isoDate"]).date(),
                content_snippet=news["contentSnippet"],
                link=news["link"],
                image_url=news["image"]['small'],
                source=source,
                classified_data=classified_info
            )
            session.add(new_article)

            session.commit()
            return {"status": "success", "message": "News inserted successfully"}
        except Exception as e:
            session.rollback()
            print(e)
            return {"status": "error", "message": str(e)}