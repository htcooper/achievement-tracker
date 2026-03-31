"""Tests for the tag suggestion module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src import tag_suggester


class TestIsConfigured:
    def test_not_configured(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert tag_suggester.is_configured() is False

    def test_configured(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            assert tag_suggester.is_configured() is True


class TestSuggestTags:
    def test_returns_empty_without_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = tag_suggester.suggest_tags("S", "A", None, [])
            assert result == []

    def test_parses_response(self) -> None:
        mock_message = MagicMock()
        mock_message.content = '["leadership", "technical"]'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
            patch("src.tag_suggester.OpenAI", return_value=mock_client),
        ):
            result = tag_suggester.suggest_tags(
                "Team needed help", "I helped", "Solved it", ["existing-tag"]
            )
            assert result == ["leadership", "technical"]

    def test_handles_markdown_wrapped_response(self) -> None:
        mock_message = MagicMock()
        mock_message.content = '```json\n["mentoring", "process"]\n```'
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
            patch("src.tag_suggester.OpenAI", return_value=mock_client),
        ):
            result = tag_suggester.suggest_tags("S", "A", None, [])
            assert result == ["mentoring", "process"]


class TestSuggestTagsAndTitle:
    def test_concurrent_suggestions(self) -> None:
        # Mock for tags
        tag_message = MagicMock()
        tag_message.content = '["leadership"]'
        tag_choice = MagicMock()
        tag_choice.message = tag_message
        tag_response = MagicMock()
        tag_response.choices = [tag_choice]

        # Mock for title
        title_message = MagicMock()
        title_message.content = "Led auth migration"
        title_choice = MagicMock()
        title_choice.message = title_message
        title_response = MagicMock()
        title_response.choices = [title_choice]

        mock_client = MagicMock()
        # Return tags first, then title
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[tag_response, title_response]
        )

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
            patch(
                "src.tag_suggester.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            result = asyncio.run(
                tag_suggester.suggest_tags_and_title(
                    "Auth was slow", "Migrated", None, []
                )
            )
            assert result["tags"] == ["leadership"]
            assert result["title"] == "Led auth migration"
