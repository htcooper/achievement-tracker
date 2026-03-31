"""AI-powered tag and title suggestions using OpenAI."""

import asyncio
import json
import os
from pathlib import Path

from openai import AsyncOpenAI, OpenAI

PROMPTS_DIR = Path(__file__).parent / "prompts"
TAG_PROMPT_PATH = PROMPTS_DIR / "tag_suggestions.txt"
TITLE_PROMPT_PATH = PROMPTS_DIR / "title_suggestion.txt"


def _load_prompt(path: Path) -> str:
    """Load a prompt template from a text file."""
    return path.read_text(encoding="utf-8")


def _format_prompt_vars(
    situation: str, action: str, result: str | None
) -> dict[str, str]:
    """Build the common template variables."""
    return {
        "situation": situation,
        "action": action,
        "result": result if result else "(not provided)",
    }


def is_configured() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def suggest_tags(
    situation: str,
    action: str,
    result: str | None,
    existing_tags: list[str],
) -> list[str]:
    """Suggest tags for an achievement using OpenAI (sync).

    Returns an empty list if the API key is not configured.
    """
    if not is_configured():
        return []

    template = _load_prompt(TAG_PROMPT_PATH)
    vars_ = _format_prompt_vars(situation, action, result)
    vars_["existing_tags"] = ", ".join(existing_tags) if existing_tags else "(none yet)"
    prompt = template.format(**vars_)

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content
    return _parse_tags_response(content)


def _parse_tags_response(content: str | None) -> list[str]:
    """Parse the JSON array from the tag suggestion response."""
    if not content:
        return []
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    tags: list[str] = json.loads(content)
    return [t.lower().strip() for t in tags if isinstance(t, str)]


async def _suggest_tags_async(
    situation: str,
    action: str,
    result: str | None,
    existing_tags: list[str],
) -> list[str]:
    """Suggest tags using async OpenAI client."""
    template = _load_prompt(TAG_PROMPT_PATH)
    vars_ = _format_prompt_vars(situation, action, result)
    vars_["existing_tags"] = ", ".join(existing_tags) if existing_tags else "(none yet)"
    prompt = template.format(**vars_)

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content
    return _parse_tags_response(content)


async def _suggest_title_async(
    situation: str,
    action: str,
    result: str | None,
) -> str | None:
    """Suggest a title using async OpenAI client."""
    template = _load_prompt(TITLE_PROMPT_PATH)
    vars_ = _format_prompt_vars(situation, action, result)
    prompt = template.format(**vars_)

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=100,
    )

    content = response.choices[0].message.content
    if not content:
        return None
    return content.strip()[:60]


async def suggest_tags_and_title(
    situation: str,
    action: str,
    result: str | None,
    existing_tags: list[str],
) -> dict[str, list[str] | str | None]:
    """Suggest both tags and title concurrently.

    Returns {"tags": [...], "title": "..." or None}.
    """
    tags_task = _suggest_tags_async(situation, action, result, existing_tags)
    title_task = _suggest_title_async(situation, action, result)

    tags, title = await asyncio.gather(tags_task, title_task)
    return {"tags": tags, "title": title}
