"""Unit tests for subscriber-related database functions."""

import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import (
    Base,
    Subscriber,
    add_subscriber,
    get_active_subscribers,
    remove_subscriber,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sqlite_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def sqlite_session(sqlite_engine):
    """Bound session for the in-memory SQLite engine."""
    TestSession = sessionmaker(bind=sqlite_engine)
    session = TestSession()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestSubscriberModel:
    def test_subscriber_table_columns(self):
        columns = {c.name for c in Subscriber.__table__.columns}
        assert {"id", "email", "is_active", "unsubscribe_token", "subscribed_at"} <= columns

    def test_email_not_nullable(self):
        col = Subscriber.__table__.columns["email"]
        assert not col.nullable

    def test_is_active_not_nullable(self):
        col = Subscriber.__table__.columns["is_active"]
        assert not col.nullable

    def test_unsubscribe_token_not_nullable(self):
        col = Subscriber.__table__.columns["unsubscribe_token"]
        assert not col.nullable


# ---------------------------------------------------------------------------
# add_subscriber tests
# ---------------------------------------------------------------------------

class TestAddSubscriber:
    def test_add_new_subscriber_success(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            result = add_subscriber("test@example.com")
        assert result["status"] == "success"
        assert "token" in result

    def test_token_is_uuid_format(self, sqlite_session):
        import uuid
        with patch("database.Session", return_value=sqlite_session):
            result = add_subscriber("uuid@example.com")
        assert result["status"] == "success"
        # Should not raise — confirms token is a valid UUID string
        uuid.UUID(result["token"])

    def test_add_duplicate_active_subscriber_returns_error(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            add_subscriber("dup@example.com")
            result = add_subscriber("dup@example.com")
        assert result["status"] == "error"
        assert "already subscribed" in result["message"].lower()

    def test_reactivate_inactive_subscriber(self, sqlite_session):
        """An unsubscribed address should be re-activated rather than duplicated."""
        with patch("database.Session", return_value=sqlite_session):
            add_subscriber("reactivate@example.com")
            remove_subscriber(
                sqlite_session.query(Subscriber)
                .filter_by(email="reactivate@example.com")
                .first()
                .unsubscribe_token
            )
            result = add_subscriber("reactivate@example.com")
        assert result["status"] == "success"
        assert "re-activated" in result["message"].lower()

    def test_subscribed_at_is_today(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            add_subscriber("today@example.com")
        row = sqlite_session.query(Subscriber).filter_by(email="today@example.com").first()
        assert row.subscribed_at == datetime.date.today()


# ---------------------------------------------------------------------------
# remove_subscriber tests
# ---------------------------------------------------------------------------

class TestRemoveSubscriber:
    def test_remove_with_valid_token(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            res = add_subscriber("remove@example.com")
            token = res["token"]
            result = remove_subscriber(token)
        assert result["status"] == "success"
        assert result.get("email") == "remove@example.com"

    def test_subscriber_is_inactive_after_removal(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            res = add_subscriber("inactive@example.com")
            remove_subscriber(res["token"])
        row = sqlite_session.query(Subscriber).filter_by(email="inactive@example.com").first()
        assert row.is_active is False

    def test_remove_with_invalid_token(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            result = remove_subscriber("00000000-0000-0000-0000-000000000000")
        assert result["status"] == "error"
        assert "invalid" in result["message"].lower() or "unknown" in result["message"].lower()

    def test_remove_already_inactive_returns_success(self, sqlite_session):
        """Calling unsubscribe twice should succeed silently."""
        with patch("database.Session", return_value=sqlite_session):
            res = add_subscriber("twice@example.com")
            remove_subscriber(res["token"])
            result = remove_subscriber(res["token"])
        assert result["status"] == "success"
        assert "already" in result["message"].lower()


# ---------------------------------------------------------------------------
# get_active_subscribers tests
# ---------------------------------------------------------------------------

class TestGetActiveSubscribers:
    def test_returns_only_active(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            add_subscriber("active@example.com")
            res = add_subscriber("inactive2@example.com")
            remove_subscriber(res["token"])
            subscribers = get_active_subscribers()
        emails = [s["email"] for s in subscribers]
        assert "active@example.com" in emails
        assert "inactive2@example.com" not in emails

    def test_returns_empty_list_when_no_subscribers(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            result = get_active_subscribers()
        assert result == []

    def test_each_entry_has_email_and_token(self, sqlite_session):
        with patch("database.Session", return_value=sqlite_session):
            add_subscriber("fields@example.com")
            subscribers = get_active_subscribers()
        assert len(subscribers) >= 1
        for sub in subscribers:
            assert "email" in sub
            assert "token" in sub
