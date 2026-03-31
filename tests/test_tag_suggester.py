"""Tests for the tag suggestion module."""

from unittest.mock import MagicMock, patch

from src import tag_suggester


class TestIsconfigured:
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
