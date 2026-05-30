"""Tests for model.py — NewsSource enum and ClassifiedNews Pydantic model."""

import json
from enum import Enum

from pydantic import ValidationError
import pytest

from model import ClassifiedNews, NewsSource


class TestNewsSource:
    """Tests for the NewsSource enum."""

    def test_enum_values(self):
        """Verify enum members have correct values."""
        assert NewsSource.CNBC.value == "cnbc-news"
        assert NewsSource.CNN.value == "cnn-news"
        assert NewsSource.REPUBLIKA.value == "republika-news"

    def test_enum_is_enum(self):
        """Verify NewsSource is a proper Enum subclass."""
        assert issubclass(NewsSource, Enum)

    def test_enum_members_count(self):
        """Verify all expected sources are present."""
        assert len(NewsSource) == 3

    def test_enum_from_value(self):
        """Verify members can be looked up by value."""
        assert NewsSource("cnbc-news") == NewsSource.CNBC
        assert NewsSource("cnn-news") == NewsSource.CNN
        assert NewsSource("republika-news") == NewsSource.REPUBLIKA


class TestClassifiedNews:
    """Tests for the ClassifiedNews Pydantic model."""

    def test_valid_model(self):
        """Verify a fully valid model is created successfully."""
        news = ClassifiedNews(
            is_highly_impactful=True,
            reasoning="Strong market indicators",
            confidence=0.85,
        )
        assert news.is_highly_impactful is True
        assert news.reasoning == "Strong market indicators"
        assert news.confidence == 0.85

    def test_non_impactful(self):
        """Verify a non-impactful classification works."""
        news = ClassifiedNews(
            is_highly_impactful=False,
            reasoning="No market relevance",
            confidence=0.3,
        )
        assert news.is_highly_impactful is False
        assert news.confidence == 0.3

    def test_confidence_range_low(self):
        """Verify confidence can be 0."""
        news = ClassifiedNews(
            is_highly_impactful=False,
            reasoning="No data",
            confidence=0.0,
        )
        assert news.confidence == 0.0

    def test_confidence_range_high(self):
        """Verify confidence can be 1."""
        news = ClassifiedNews(
            is_highly_impactful=True,
            reasoning="Certain",
            confidence=1.0,
        )
        assert news.confidence == 1.0

    @pytest.mark.parametrize("invalid_confidence", [-0.1, 1.5, 2.0, -1])
    def test_confidence_out_of_range(self, invalid_confidence: float):
        """Verify confidence outside [0,1] raises validation error."""
        with pytest.raises(ValidationError):
            ClassifiedNews(
                is_highly_impactful=True,
                reasoning="Test",
                confidence=invalid_confidence,
            )

    def test_missing_required_fields(self):
        """Verify missing required fields raises validation error."""
        with pytest.raises(ValidationError):
            ClassifiedNews()  # type: ignore[call-arg]

    def test_json_schema(self):
        """Verify JSON schema generation works (used in the API call)."""
        schema = ClassifiedNews.model_json_schema()
        assert "is_highly_impactful" in schema.get("properties", {})
        assert "reasoning" in schema.get("properties", {})
        assert "confidence" in schema.get("properties", {})

    def test_model_dump_json(self):
        """Verify model can be serialized to JSON."""
        news = ClassifiedNews(
            is_highly_impactful=True,
            reasoning="Test reasoning",
            confidence=0.9,
        )
        data = news.model_dump()
        assert data["is_highly_impactful"] is True
        assert data["reasoning"] == "Test reasoning"
        assert data["confidence"] == 0.9

    def test_model_extra_fields_forbidden(self):
        """Verify extra fields are not allowed by default."""
        with pytest.raises(ValidationError):
            ClassifiedNews(
                is_highly_impactful=True,
                reasoning="Test",
                confidence=0.5,
                extra_field="should_not_work",
            )
