"""Tests for news.py — main application logic."""

import json
from unittest.mock import MagicMock

import pytest
import responses
from pytest_mock import MockerFixture

from news import (
    NewsSource,
    build_email_body,
    classify_news,
    get_news,
    main,
    send_email,
)


class TestGetNews:
    """Tests for get_news() function."""

    @responses.activate
    def test_get_news_success(self, sample_cnbc_news: dict):
        """Verify get_news returns parsed JSON on success."""
        url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, url, json=sample_cnbc_news, status=200)

        result = get_news(NewsSource.CNBC)
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["title"] == "Market Update: IHSG Menguat Hari Ini"

    @responses.activate
    def test_get_news_with_type(self, sample_cnbc_news: dict):
        """Verify get_news appends type to URL when provided."""
        url = "https://berita-indo-api-next.vercel.app/api/cnbc-news/market"
        responses.add(responses.GET, url, json=sample_cnbc_news, status=200)

        result = get_news(NewsSource.CNBC, type="market")
        assert result is not None
        assert "data" in result

    @responses.activate
    def test_get_news_http_error(self):
        """Verify get_news returns None on HTTP error."""
        url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, url, status=500)

        result = get_news(NewsSource.CNBC)
        assert result is None

    @responses.activate
    def test_get_news_network_error(self):
        """Verify get_news returns None on network error."""
        url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, url, body=ConnectionError("Network error"))

        result = get_news(NewsSource.CNBC)
        assert result is None

    @responses.activate
    def test_get_news_invalid_json(self):
        """Verify get_news returns None on invalid JSON response."""
        url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, url, body="not-json", status=200)

        result = get_news(NewsSource.CNBC)
        assert result is None

    def test_get_news_correct_urls(self):
        """Verify each NewsSource maps to the correct API URL."""
        expected_urls = {
            NewsSource.CNBC: "https://berita-indo-api-next.vercel.app/api/cnbc-news",
            NewsSource.CNN: "https://berita-indo-api-next.vercel.app/api/cnn-news",
            NewsSource.REPUBLIKA: "https://berita-indo-api-next.vercel.app/api/republika-news",
        }
        for source, expected_url in expected_urls.items():
            with responses.RequestsMock() as rsps:
                rsps.add(responses.GET, expected_url, json={"data": []}, status=200)
                result = get_news(source)
                assert result is not None


class TestClassifyNews:
    """Tests for classify_news() function."""

    def test_classify_success(self, mocker: MockerFixture, mock_hf_client: MagicMock):
        """Verify classify_news returns structured data on success."""
        news_item = {
            "contentSnippet": "IHSG menguat signifikan pada perdagangan hari ini.",
            "link": "https://example.com/test",
        }
        result = classify_news(news_item)
        assert result["is_highly_impactful"] is True
        assert "confidence" in result
        assert "reasoning" in result

    def test_classify_missing_content_snippet(self):
        """Verify classify_news raises ValueError when contentSnippet is missing."""
        news_item = {"link": "https://example.com/no-snippet"}
        with pytest.raises(ValueError, match="content snippet / description is required"):
            classify_news(news_item)

    def test_classify_empty_content_snippet(self):
        """Verify classify_news raises ValueError when contentSnippet is empty."""
        news_item = {"contentSnippet": "", "link": "https://example.com/empty"}
        with pytest.raises(ValueError, match="content snippet / description is required"):
            classify_news(news_item)

    def test_classify_api_failure_returns_fallback(
        self, mocker: MockerFixture
    ):
        """Verify classify_news returns fallback dict after all retries fail."""
        mock_client = mocker.patch("news.client")
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        news_item = {
            "contentSnippet": "Some news content here.",
            "link": "https://example.com/api-fail",
        }
        result = classify_news(news_item)
        assert result["is_highly_impactful"] is False
        assert result["confidence"] == 0.0
        assert "Failed to classify" in result["reasoning"]

    def test_classify_retries_on_failure(self, mocker: MockerFixture):
        """Verify classify_news retries up to 3 times on failure."""
        mock_client = mocker.patch("news.client")
        mock_client.chat.completions.create.side_effect = [
            Exception("Attempt 1 failed"),
            Exception("Attempt 2 failed"),
            Exception("Attempt 3 failed"),
        ]

        news_item = {
            "contentSnippet": "Retry test content.",
            "link": "https://example.com/retry",
        }
        result = classify_news(news_item)
        assert mock_client.chat.completions.create.call_count == 3
        assert result["is_highly_impactful"] is False

    def test_classify_succeeds_on_second_retry(
        self, mocker: MockerFixture
    ):
        """Verify classify_news succeeds on the second attempt after a failure."""
        mock_client = mocker.patch("news.client")

        # First call fails, second succeeds
        mock_completion = mocker.MagicMock()
        mock_choice = mocker.MagicMock()
        mock_choice.message.content = json.dumps({
            "is_highly_impactful": True,
            "reasoning": "Recovered after retry.",
            "confidence": 0.8,
        })
        mock_completion.choices = [mock_choice]

        mock_client.chat.completions.create.side_effect = [
            Exception("First attempt failed"),
            mock_completion,
        ]

        news_item = {
            "contentSnippet": "Second time's the charm.",
            "link": "https://example.com/retry-success",
        }
        result = classify_news(news_item)
        assert result["is_highly_impactful"] is True
        assert result["confidence"] == 0.8


class TestSendEmail:
    """Tests for send_email() function."""

    def test_send_email_success(self, mocker: MockerFixture, mock_email: MagicMock):
        """Verify send_email calls resend API with correct parameters."""
        result = send_email(
            subject="Test Subject",
            body="<p>Test body</p>",
            to="test@example.com",
        )
        assert result == {"id": "test-email-id"}
        mock_email.assert_called_once_with({
            "from": "Felix <onboarding@mail.felix-antony.com>",
            "to": "test@example.com",
            "subject": "Test Subject",
            "html": "<p>Test body</p>",
        })

    def test_send_email_to_list(self, mocker: MockerFixture, mock_email: MagicMock):
        """Verify send_email works with a list of recipients."""
        recipients = ["a@example.com", "b@example.com"]
        send_email(subject="S", body="B", to=recipients)
        mock_email.assert_called_once()
        assert mock_email.call_args[0][0]["to"] == recipients

    def test_send_email_failure_logged(self, mocker: MockerFixture):
        """Verify send_email logs an error on failure (doesn't crash)."""
        mock_send = mocker.patch("news.resend.Emails.send")
        mock_send.side_effect = Exception("Email API error")

        # Should not raise, just log
        result = send_email(
            subject="Test",
            body="Body",
            to="test@example.com",
        )
        assert result is None


class TestBuildEmailBody:
    """Tests for build_email_body() function."""

    def test_build_email_body_empty(self):
        """Verify empty list produces valid HTML with zero count."""
        result = build_email_body([])
        assert "<html" in result
        assert "Found <strong>0</strong> highly impactful" in result
        assert "Daily Market Impact" in result

    def test_build_email_body_single_item(
        self, sample_cnbc_news: dict, sample_classified_impactful: dict
    ):
        """Verify single news item produces correct HTML."""
        item = sample_cnbc_news["data"][0]
        result = build_email_body([(item, sample_classified_impactful)])

        assert "<html" in result
        assert "Found <strong>1</strong> highly impactful" in result
        assert item["title"] in result
        assert "85% confidence" in result
        assert sample_classified_impactful["reasoning"] in result

    def test_build_email_body_multiple_items(
        self, sample_cnbc_news: dict,
        sample_classified_impactful: dict,
        sample_classified_non_impactful: dict,
    ):
        """Verify multiple news items each produce a card."""
        item1 = sample_cnbc_news["data"][0]
        item2 = sample_cnbc_news["data"][1]
        result = build_email_body([
            (item1, sample_classified_impactful),
            (item2, sample_classified_non_impactful),
        ])

        assert "Found <strong>2</strong> highly impactful" in result
        assert item1["title"] in result
        assert item2["title"] in result
        assert item1["link"] in result

    def test_build_email_body_html_structure(self, sample_cnbc_news: dict):
        """Verify the HTML structure has all expected sections."""
        item = sample_cnbc_news["data"][0]
        result = build_email_body([(item, {"is_highly_impactful": True, "reasoning": "Test", "confidence": 0.9})])

        # Check HTML structure
        assert result.startswith("<!DOCTYPE html>")
        assert "<html" in result
        assert "</html>" in result
        assert "<head>" in result
        assert "<body" in result
        # Check key sections
        assert "Daily Market Impact" in result
        assert "Why it matters:" in result

    def test_build_email_body_truncates_long_snippet(self):
        """Verify content snippets longer than 200 chars are truncated."""
        long_snippet = "A" * 250
        item = {
            "title": "Long snippet test",
            "link": "https://example.com/long",
            "contentSnippet": long_snippet,
            "isoDate": "2026-05-30T10:00:00.000Z",
            "image": {"small": "https://example.com/img.jpg"},
        }
        classified = {"is_highly_impactful": True, "reasoning": "Test", "confidence": 0.5}
        result = build_email_body([(item, classified)])

        # The snippet should be truncated to 200 chars + ellipsis
        assert "A" * 200 in result
        assert "A" * 250 not in result
        assert "…" in result


class TestMain:
    """Tests for main() function — the main orchestration logic."""

    @responses.activate
    def test_main_processes_all_sources(
        self,
        mocker: MockerFixture,
        sample_cnbc_news: dict,
        sample_republika_news: dict,
        mock_hf_client: MagicMock,
        mock_db_queries: None,
        mock_email: MagicMock,
        mock_env_vars: None,
    ):
        """Verify main() fetches from all sources and processes news."""
        # Register mock responses for all 3 news sources
        cnbc_url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        cnn_url = "https://berita-indo-api-next.vercel.app/api/cnn-news"
        republika_url = "https://berita-indo-api-next.vercel.app/api/republika-news"

        responses.add(responses.GET, cnbc_url, json=sample_cnbc_news, status=200)
        responses.add(responses.GET, cnn_url, json={"data": []}, status=200)
        responses.add(responses.GET, republika_url, json=sample_republika_news, status=200)

        main()

        # Verify all sources were processed
        assert mock_email.called, "Email should have been sent with impactful news"

        # Check HuggingFace was called for each news item with contentSnippet
        call_count = mock_hf_client.chat.completions.create.call_count
        # 2 CNBC items + 0 CNN items + 1 Republika item (after renaming description->contentSnippet)
        assert call_count == 3

    @responses.activate
    def test_main_no_impactful_news_skips_email(
        self,
        mocker: MockerFixture,
        sample_cnbc_news: dict,
        mock_db_queries: None,
        mock_env_vars: None,
    ):
        """Verify main() skips sending email when no news is classified as impactful."""
        # Make HF return non-impactful classification
        mock_completion = mocker.MagicMock()
        mock_choice = mocker.MagicMock()
        mock_choice.message.content = json.dumps({
            "is_highly_impactful": False,
            "reasoning": "Not relevant.",
            "confidence": 0.6,
        })
        mock_completion.choices = [mock_choice]
        mock_client = mocker.patch("news.client")
        mock_client.chat.completions.create.return_value = mock_completion

        cnn_url = "https://berita-indo-api-next.vercel.app/api/cnn-news"
        responses.add(responses.GET, cnn_url, json={"data": []}, status=200)
        cnbc_url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, cnbc_url, json=sample_cnbc_news, status=200)
        republika_url = "https://berita-indo-api-next.vercel.app/api/republika-news"
        responses.add(responses.GET, republika_url, json={"data": []}, status=200)

        mock_email = mocker.patch("news.resend.Emails.send")

        main()

        assert not mock_email.called, "Email should NOT be sent when no impactful news"

    @responses.activate
    def test_main_skips_duplicate_news(
        self,
        mocker: MockerFixture,
        sample_cnbc_news: dict,
        mock_hf_client: MagicMock,
        mock_env_vars: None,
    ):
        """Verify main() skips news that already exists in the database."""
        # Mock query_news to return an existing record (simulating duplicate)
        mocker.patch("news.query_news", return_value=MagicMock())

        cnbc_url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        responses.add(responses.GET, cnbc_url, json=sample_cnbc_news, status=200)
        cnn_url = "https://berita-indo-api-next.vercel.app/api/cnn-news"
        responses.add(responses.GET, cnn_url, json={"data": []}, status=200)
        republika_url = "https://berita-indo-api-next.vercel.app/api/republika-news"
        responses.add(responses.GET, republika_url, json={"data": []}, status=200)

        mock_insert = mocker.patch("news.insert_news")

        main()

        # News items should NOT be inserted since they already exist
        mock_insert.assert_not_called()

    @responses.activate
    def test_main_api_failure_continues(
        self,
        mocker: MockerFixture,
        sample_cnbc_news: dict,
        sample_republika_news: dict,
        mock_hf_client: MagicMock,
        mock_db_queries: None,
        mock_email: MagicMock,
        mock_env_vars: None,
    ):
        """Verify main() continues processing other sources if one API fails."""
        # CNBC fails, CNN and Republika succeed
        cnbc_url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        cnn_url = "https://berita-indo-api-next.vercel.app/api/cnn-news"
        republika_url = "https://berita-indo-api-next.vercel.app/api/republika-news"

        responses.add(responses.GET, cnbc_url, status=500)
        responses.add(responses.GET, cnn_url, json={"data": []}, status=200)
        responses.add(responses.GET, republika_url, json=sample_republika_news, status=200)

        main()

        # Should still continue despite CNBC failure
        assert mock_email.called, "Email should still be sent from Republika news"

    @responses.activate
    def test_main_republika_renames_description(
        self,
        mocker: MockerFixture,
        sample_republika_news: dict,
        mock_hf_client: MagicMock,
        mock_db_queries: None,
        mock_env_vars: None,
    ):
        """Verify Republika news has 'description' renamed to 'contentSnippet'."""
        mocker.patch("news.query_news", return_value=None)

        cnbc_url = "https://berita-indo-api-next.vercel.app/api/cnbc-news"
        cnn_url = "https://berita-indo-api-next.vercel.app/api/cnn-news"
        republika_url = "https://berita-indo-api-next.vercel.app/api/republika-news"

        responses.add(responses.GET, cnbc_url, json={"data": []}, status=200)
        responses.add(responses.GET, cnn_url, json={"data": []}, status=200)
        responses.add(responses.GET, republika_url, json=sample_republika_news, status=200)

        # Patch classify_news to capture what it receives
        original_classify = classify_news
        captured_items = []

        def tracking_classify(item):
            captured_items.append(item)
            return original_classify(item)

        mocker.patch("news.classify_news", side_effect=tracking_classify)

        main()

        # Verify the Republika item has contentSnippet (not description)
        republika_item = next(
            (item for item in captured_items if "republika" in item.get("link", "")),
            None
        )
        assert republika_item is not None
        assert "contentSnippet" in republika_item
        assert "description" not in republika_item
        assert republika_item["contentSnippet"] == sample_republika_news["data"][0]["description"]
