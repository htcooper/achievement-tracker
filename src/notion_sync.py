"""Notion integration for promoting achievements to STAR-format pages."""

import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_headers() -> dict[str, str]:
    """Get Notion API headers."""
    api_key = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _notion_request(
    method: str, endpoint: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Make a request to the Notion API."""
    url = f"{NOTION_API_URL}/{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=_get_headers(), method=method)
    with urlopen(req) as resp:
        result: dict[str, Any] = json.loads(resp.read().decode())
        return result


def _get_or_create_database() -> str:
    """Get the database ID from env, or create a new database."""
    db_id = os.getenv("NOTION_DATABASE_ID", "")
    if db_id:
        return db_id

    # To create a database, we need a parent page
    # The user should set NOTION_DATABASE_ID after creating it
    # For now, raise an informative error
    raise RuntimeError(
        "NOTION_DATABASE_ID is not set. Please create a Notion database with "
        "properties: Title (title), Situation (rich_text), Task (rich_text), "
        "Action (rich_text), Result (rich_text), Tags (multi_select), Date (date), "
        "then set the database ID in your .env file."
    )


def promote_to_notion(
    achievement: dict[str, Any],
    star_narrative: dict[str, str],
    screenshot_paths: list[Path] | None = None,
) -> str:
    """Create a Notion page from an achievement with STAR narrative.

    Returns the Notion page ID.
    """
    database_id = _get_or_create_database()

    # Build the page properties
    title = star_narrative["situation"][:100]  # Truncate for title
    tags = achievement.get("tags", [])

    properties: dict[str, Any] = {
        "Title": {
            "title": [{"text": {"content": title}}],
        },
        "Situation": {
            "rich_text": [{"text": {"content": star_narrative["situation"]}}],
        },
        "Task": {
            "rich_text": [{"text": {"content": star_narrative["task"]}}],
        },
        "Action": {
            "rich_text": [{"text": {"content": star_narrative["action"]}}],
        },
        "Result": {
            "rich_text": [{"text": {"content": star_narrative["result"]}}],
        },
        "Tags": {
            "multi_select": [{"name": tag} for tag in tags],
        },
        "Date": {
            "date": {"start": achievement["created_at"][:10]},
        },
    }

    # Build page content blocks with STAR sections
    children: list[dict[str, Any]] = [
        _heading_block("Situation"),
        _paragraph_block(star_narrative["situation"]),
        _heading_block("Task"),
        _paragraph_block(star_narrative["task"]),
        _heading_block("Action"),
        _paragraph_block(star_narrative["action"]),
        _heading_block("Result"),
        _paragraph_block(star_narrative["result"]),
    ]

    # Note: Notion API doesn't support file uploads directly in page creation.
    # Screenshots would need to be uploaded to an external host first.
    # For now, we add a note about local screenshots if any exist.
    if screenshot_paths:
        children.append(_heading_block("Screenshots"))
        children.append(
            _paragraph_block(
                f"{len(screenshot_paths)} screenshot(s) available locally."
            )
        )

    page_data: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": properties,
        "children": children,
    }

    result = _notion_request("POST", "pages", page_data)
    page_id: str = result["id"]
    return page_id


def _heading_block(text: str) -> dict[str, Any]:
    """Create a Notion heading_2 block."""
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    }


def _paragraph_block(text: str) -> dict[str, Any]:
    """Create a Notion paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    }
