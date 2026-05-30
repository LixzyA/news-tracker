"""Shared fixtures for news-tracker tests."""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import responses
from pytest_mock import MockerFixture

# --- Sample data fixtures ---

SAMPLE_CNBC_NEWS = {
    "data": [
        {
            "title": "Market Update: IHSG Menguat Hari Ini",
            "link": "https://www.cnbcindonesia.com/market/20260530-test-001",
            "contentSnippet": "Indeks Harga Saham Gabungan (IHSG) menguat signifikan pada perdagangan hari ini didorong oleh sentimen positif dari pasar global.",
            "isoDate": "2026-05-30T10:00:00.000Z",
            "image": {
                "small": "https://img.example.com/ihsg.jpg",
                "large": "https://img.example.com/ihsg-large.jpg"
            },
            "source": "cnbc-news"
        },
        {
            "title": "Rupiah Terus Melemah di Tengah Ketidakpastian Global",
            "link": "https://www.cnbcindonesia.com/market/20260530-test-002",
            "contentSnippet": "Nilai tukar rupiah terus melemah terhadap dolar AS di tengah ketidakpastian ekonomi global dan kebijakan suku bunga The Fed.",
            "isoDate": "2026-05-30T09:00:00.000Z",
            "image": {
                "small": "https://img.example.com/rupiah.jpg",
                "large": "https://img.example.com/rupiah-large.jpg"
            },
            "source": "cnbc-news"
        }
    ]
}

SAMPLE_REPUBLIKA_NEWS = {
    "data": [
        {
            "title": "Ekonomi Indonesia Tumbuh Positif di Kuartal II",
            "link": "https://ekonomi.republika.co.id/berita/test001",
            "description": "Pertumbuhan ekonomi Indonesia menunjukkan tren positif didukung oleh konsumsi domestik dan investasi.",
            "isoDate": "2026-05-30T08:00:00.000Z",
            "image": {
                "small": "https://img.example.com/ekonomi.jpg"
            },
            "source": "republika-news"
        }
    ]
}

SAMPLE_CLASSIFIED_IMPACTFUL = {
    "is_highly_impactful": True,
    "reasoning": "This news discusses stock market movements that directly impact investor sentiment.",
    "confidence": 0.85
}

SAMPLE_CLASSIFIED_NON_IMPACTFUL = {
    "is_highly_impactful": False,
    "reasoning": "This news does not contain information relevant to the stock market.",
    "confidence": 0.75
}


@pytest.fixture
def sample_cnbc_news() -> dict:
    return SAMPLE_CNBC_NEWS


@pytest.fixture
def sample_republika_news() -> dict:
    return SAMPLE_REPUBLIKA_NEWS


@pytest.fixture
def sample_classified_impactful() -> dict:
    return dict(SAMPLE_CLASSIFIED_IMPACTFUL)


@pytest.fixture
def sample_classified_non_impactful() -> dict:
    return dict(SAMPLE_CLASSIFIED_NON_IMPACTFUL)


@pytest.fixture
def mock_env_vars(mocker: MockerFixture) -> None:
    """Set up mock environment variables for testing."""
    mocker.patch.dict(os.environ, {
        "HF_TOKEN": "test-hf-token",
        "RESEND_API_KEY": "test-resend-key",
        "user": "test_user",
        "password": "test_password",
        "host": "localhost",
        "port": "5432",
        "dbname": "test_db",
    })


@pytest.fixture
def mock_hf_client(mocker: MockerFixture) -> None:
    """Mock the HuggingFace InferenceClient to return structured responses."""
    mock_completion = mocker.MagicMock()
    mock_choice = mocker.MagicMock()
    mock_choice.message.content = json.dumps(SAMPLE_CLASSIFIED_IMPACTFUL)
    mock_completion.choices = [mock_choice]

    mock_client = mocker.patch("news.client")
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_db_queries(mocker: MockerFixture) -> None:
    """Mock database functions to avoid requiring a real database."""
    mocker.patch("news.query_news", return_value=None)
    mocker.patch("news.insert_news", return_value={"status": "success", "message": "OK"})


@pytest.fixture
def mock_email(mocker: MockerFixture) -> None:
    """Mock the resend email API."""
    mock_resend = mocker.patch("news.resend.Emails.send")
    mock_resend.return_value = {"id": "test-email-id"}
    return mock_resend


@pytest.fixture
def prompt_file() -> Generator[Path, None, None]:
    """Create a temporary prompt.txt for testing."""
    # Ensure the original prompt.txt exists for tests that need it
    prompt_path = Path.cwd() / "prompt.txt"
    if not prompt_path.exists():
        prompt_path.write_text("You are a test assistant.")
    yield prompt_path
