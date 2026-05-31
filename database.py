from sqlalchemy import Boolean, Float, String, create_engine, ForeignKey, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, Session, relationship, declarative_base
from sqlalchemy.types import Date, Integer
import datetime
import uuid
from dotenv import load_dotenv
import os
from logger import setup_logger

logger = setup_logger(__name__)
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
    is_impactful: Mapped[bool] = mapped_column(Boolean, nullable=False)
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
            if news_list:
                logger.info(f"Queried news with link '{link}' found in database.")
                return news_list
    except Exception as e:
        logger.exception(f"Error occurred while querying news with link '{link}': {e}")
        raise 

def insert_news(news: dict, source: str, classified_data: dict):
    logger.debug(f"Inserting news with title '{news['title']}' into database.")
    with Session(engine) as session:
        try:
            
            classified_info = ClassifiedNews(
                is_impactful= classified_data["is_highly_impactful"],
                confidence= classified_data["confidence"],
                reason= classified_data["reasoning"]
            )
            logger.debug(f"Classified info: {classified_info}")

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
            logger.debug(f"News with title '{news['title']}' inserted successfully.")
            return {"status": "success", "message": "News inserted successfully"}
        except Exception as e:
            session.rollback()
            logger.error(f"Error occurred while inserting news: {e}")
            return {"status": "error", "message": str(e)}


def add_subscriber(email: str) -> dict:
    """Insert a new active subscriber. Returns an error dict if the email is already subscribed."""
    with Session(engine) as session:
        try:
            existing = session.query(Subscriber).where(Subscriber.email == email).first()
            if existing:
                if existing.is_active:
                    logger.info(f"Subscription attempt for already-active email: {email}")
                    return {"status": "error", "message": "Email is already subscribed."}
                # Re-activate a previously unsubscribed address
                existing.is_active = True
                existing.subscribed_at = datetime.date.today()
                session.commit()
                logger.info(f"Re-activated subscriber: {email}")
                return {"status": "success", "message": "Subscription re-activated."}

            token = str(uuid.uuid4())
            subscriber = Subscriber(
                email=email,
                is_active=True,
                unsubscribe_token=token,
                subscribed_at=datetime.date.today(),
            )
            session.add(subscriber)
            session.commit()
            logger.info(f"New subscriber added: {email}")
            return {"status": "success", "message": "Subscribed successfully.", "token": token}
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding subscriber {email}: {e}")
            return {"status": "error", "message": str(e)}


def remove_subscriber(token: str) -> dict:
    """Deactivate the subscriber whose unsubscribe token matches. Returns an error dict if not found."""
    with Session(engine) as session:
        try:
            subscriber = session.query(Subscriber).where(Subscriber.unsubscribe_token == token).first()
            if not subscriber:
                logger.warning(f"Unsubscribe attempt with unknown token: {token}")
                return {"status": "error", "message": "Invalid or unknown unsubscribe token."}
            if not subscriber.is_active:
                return {"status": "success", "message": "Already unsubscribed."}
            subscriber.is_active = False
            session.commit()
            logger.info(f"Subscriber deactivated: {subscriber.email}")
            return {"status": "success", "message": "Unsubscribed successfully.", "email": subscriber.email}
        except Exception as e:
            session.rollback()
            logger.error(f"Error removing subscriber with token {token}: {e}")
            return {"status": "error", "message": str(e)}


def get_active_subscribers() -> list[dict]:
    """Return a list of dicts with 'email' and 'unsubscribe_token' for every active subscriber."""
    with Session(engine) as session:
        rows = session.query(Subscriber).where(Subscriber.is_active == True).all()  # noqa: E712
        logger.info(f"Retrieved {len(rows)} active subscriber(s).")
        return [{"email": row.email, "token": row.unsubscribe_token} for row in rows]