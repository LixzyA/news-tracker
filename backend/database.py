from typing import List
from sqlalchemy import Boolean, Float, String, create_engine, ForeignKey, UniqueConstraint, ARRAY
from sqlalchemy.orm import mapped_column, Mapped, Session, relationship, declarative_base
from sqlalchemy.types import Date, Integer
import datetime
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = int(os.getenv("port", 5432))
DB_NAME = os.getenv("dbname")
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}", pool_pre_ping=True,
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
    is_high_impact: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    impact_category: Mapped[str] = mapped_column(String(50), nullable=False)
    affected_sectors: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)  # Store as an array of strings
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(), nullable=True)
    news: Mapped["News"] = relationship(back_populates="classified_data")


class Subscriber(Base):
    __tablename__ = "subscribers"
    __table_args__ = (UniqueConstraint("email", name="uq_subscriber_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unsubscribe_token: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    subscribed_at: Mapped[datetime.date] = mapped_column(Date, nullable=False)


Base.metadata.create_all(engine)


def query_news(link: str) -> News | None:
    try:
        with Session(engine) as session:
            news_list = session.query(News).where(News.link == link).first()
            if not news_list:
                return None
            return news_list
    except Exception as e:
        raise ValueError(f"Database query error: {str(e)}")

def insert_news(news: dict, source: str, classified_data: dict) -> None:
    with Session(engine) as session:
        try:
            # Map incoming classified_data permissively to canonical DB fields
            reason_val = classified_data.get("reason") or classified_data.get("reasoning")

            classified_info = ClassifiedNews(
                is_high_impact=classified_data.get("is_high_impact", False),
                confidence=classified_data.get("confidence", 0.0),
                sentiment=classified_data.get("sentiment", "neutral"),
                impact_category=classified_data.get("impact_category", "none"),
                affected_sectors=classified_data.get("affected_sectors", []),
                reason=reason_val,
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
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error inserting news: {str(e)}")


def add_subscriber(email: str) -> None:
    """Insert a new active subscriber. Return if the email is already subscribed."""
    with Session(engine) as session:
        try:
            existing = session.query(Subscriber).where(Subscriber.email == email).first()
            if existing:
                if existing.is_active:
                    return None  # Already subscribed, no action needed
                # Re-activate a previously unsubscribed address
                existing.is_active = True
                existing.subscribed_at = datetime.date.today()
                session.commit()
                return None

            token = str(uuid.uuid4())
            subscriber = Subscriber(
                email=email,
                is_active=True,
                unsubscribe_token=token,
                subscribed_at=datetime.date.today(),
            )
            session.add(subscriber)
            session.commit()
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error adding subscriber {email}: {str(e)}")


def remove_subscriber(token: str) -> None:
    """Deactivate the subscriber whose unsubscribe token matches. Raises an error if not found."""
    with Session(engine) as session:
        try:
            subscriber = session.query(Subscriber).where(Subscriber.unsubscribe_token == token).first()
            if not subscriber:
                raise ValueError("Invalid or unknown unsubscribe token.")
            if not subscriber.is_active:
                return None  # Already unsubscribed, no action needed
            subscriber.is_active = False
            session.commit()
        except Exception as e:
            session.rollback()
            raise ValueError(f"Error removing subscriber with token {token}: {str(e)}")


def get_active_subscribers() -> list[dict]:
    """Return a list of dicts with 'email' and 'unsubscribe_token' for every active subscriber."""
    with Session(engine) as session:
        rows = session.query(Subscriber).where(Subscriber.is_active == True).all()  # noqa: E712
        return [{"email": row.email, "token": row.unsubscribe_token} for row in rows]