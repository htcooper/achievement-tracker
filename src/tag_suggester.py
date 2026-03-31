"""AI-powered tag suggestions using OpenAI."""

import json
import os
from pathlib import Path

from openai import OpenAI

PROMPT_PATH = Path(__file__).parent / "prompts" / "tag_suggestions.txt"


def _load_prompt_template() -> str:
    """Load the prompt template from the editable text file."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def is_configured() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def suggest_tags(
    situation: str,
    action: str,
    result: str | None,
    existing_tags: list[str],
) -> list[str]:
    """Suggest tags for an achievement using OpenAI.

    Returns an empty list if the API key is not configured or if the call fails.
    """
    if not is_configured():
        return []

    template = _load_prompt_template()

    existing_tags_str = ", ".join(existing_tags) if existing_tags else "(none yet)"
    result_str = result if result else "(not provided)"

    prompt = template.format(
        existing_tags=existing_tags_str,
        situation=situation,
        action=action,
        result=result_str,
    )

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content
    if not content:
        return []

    # Parse the JSON array from the response
    content = content.strip()
    # Handle potential markdown code block wrapping
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    tags: list[str] = json.loads(content)
    return [t.lower().strip() for t in tags if isinstance(t, str)]
