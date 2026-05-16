"""FastAPI application with achievement tracker routes."""

import csv
import io
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from src import database as db
from src import notion_sync, tag_suggester
from src.models import (
    AchievementCreate,
    AchievementResponse,
    AchievementUpdate,
    PromoteRequest,
    RewriteRequest,
    RewriteResponse,
    TagSuggestRequest,
    TagSuggestResponse,
    TagWithCount,
    TitleSuggestResponse,
)

load_dotenv()

STATIC_DIR = Path(__file__).parent.parent / "static"
SCREENSHOTS_DIR = Path(__file__).parent.parent / "data" / "screenshots"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Achievement Tracker", lifespan=lifespan)


# --- Achievement CRUD ---


@app.post("/api/achievements", response_model=AchievementResponse)
def create_achievement(body: AchievementCreate) -> AchievementResponse:
    result = db.add_achievement(
        situation=body.situation,
        task=body.task,
        action=body.action,
        result=body.result,
        tags=body.tags,
        title=body.title,
        company=body.company,
    )
    return AchievementResponse(**result)


@app.get("/api/achievements", response_model=list[AchievementResponse])
def list_achievements(
    q: Annotated[str | None, Query()] = None,
    tags: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    company: Annotated[str | None, Query()] = None,
    archived: Annotated[bool, Query()] = False,
) -> list[AchievementResponse]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = db.search_achievements(
        query=q,
        tags=tag_list,
        date_from=date_from,
        date_to=date_to,
        company=company,
        include_archived=archived,
    )
    return [AchievementResponse(**r) for r in results]


@app.get("/api/achievements/{achievement_id}", response_model=AchievementResponse)
def get_achievement(achievement_id: int) -> AchievementResponse:
    result = db.get_achievement_by_id(achievement_id)
    if not result:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return AchievementResponse(**result)


@app.put("/api/achievements/{achievement_id}", response_model=AchievementResponse)
def update_achievement(
    achievement_id: int, body: AchievementUpdate
) -> AchievementResponse:
    result = db.update_achievement(
        achievement_id=achievement_id,
        title=body.title,
        company=body.company,
        situation=body.situation,
        task=body.task,
        action=body.action,
        result=body.result,
        tags=body.tags,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return AchievementResponse(**result)


@app.delete("/api/achievements/{achievement_id}")
def delete_achievement(achievement_id: int) -> dict[str, bool]:
    if not db.delete_achievement(achievement_id):
        raise HTTPException(status_code=404, detail="Achievement not found")
    return {"deleted": True}


# --- Archive ---


@app.patch(
    "/api/achievements/{achievement_id}/archive", response_model=AchievementResponse
)
def toggle_archive(achievement_id: int) -> AchievementResponse:
    result = db.toggle_archive(achievement_id)
    if not result:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return AchievementResponse(**result)


# --- Tags ---


@app.get("/api/tags", response_model=list[TagWithCount])
def get_tags() -> list[TagWithCount]:
    return [TagWithCount(**t) for t in db.get_all_tags()]


# --- Companies ---


@app.get("/api/companies", response_model=list[str])
def get_companies() -> list[str]:
    return db.get_all_companies()


# --- AI Tag Suggestions ---


@app.get("/api/config/features")
def get_features() -> dict[str, bool]:
    """Return which optional features are configured."""
    return {
        "ai_tags": tag_suggester.is_configured(),
        "notion": bool(os.getenv("NOTION_API_KEY")),
    }


@app.post("/api/suggest-tags", response_model=TagSuggestResponse)
async def suggest_tags(body: TagSuggestRequest) -> TagSuggestResponse:
    if not tag_suggester.is_configured():
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    existing = [t["tag"] for t in db.get_all_tags()]
    tags = await tag_suggester._suggest_tags_async(
        situation=body.situation,
        action=body.action,
        result=body.result,
        existing_tags=existing,
    )
    return TagSuggestResponse(suggested_tags=tags)


@app.post("/api/rewrite-field", response_model=RewriteResponse)
async def rewrite_field(body: RewriteRequest) -> RewriteResponse:
    if not tag_suggester.is_configured():
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    rewritten = await tag_suggester.rewrite_field_async(body.field, body.text)
    return RewriteResponse(rewritten_text=rewritten)


@app.post("/api/suggest-title", response_model=TitleSuggestResponse)
async def suggest_title(body: TagSuggestRequest) -> TitleSuggestResponse:
    if not tag_suggester.is_configured():
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    title = await tag_suggester._suggest_title_async(
        situation=body.situation,
        action=body.action,
        result=body.result,
    )
    return TitleSuggestResponse(suggested_title=title)


# --- Notion Promote ---


@app.post(
    "/api/achievements/{achievement_id}/promote", response_model=AchievementResponse
)
def promote_to_notion(achievement_id: int, body: PromoteRequest) -> AchievementResponse:
    achievement = db.get_achievement_by_id(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    if not os.getenv("NOTION_API_KEY"):
        raise HTTPException(status_code=503, detail="Notion API key not configured")

    # Collect screenshot paths for this achievement
    screenshot_dir = SCREENSHOTS_DIR / str(achievement_id)
    screenshot_paths: list[Path] = []
    if screenshot_dir.exists():
        screenshot_paths = sorted(screenshot_dir.iterdir())

    try:
        notion_page_id = notion_sync.promote_to_notion(
            achievement=achievement,
            star_narrative={
                "situation": body.situation,
                "task": body.task,
                "action": body.action,
                "result": body.result,
            },
            screenshot_paths=screenshot_paths,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    db.set_notion_page_id(achievement_id, notion_page_id)
    updated = db.get_achievement_by_id(achievement_id)
    assert updated is not None
    return AchievementResponse(**updated)


@app.patch(
    "/api/achievements/{achievement_id}/promote", response_model=AchievementResponse
)
def sync_to_notion(achievement_id: int, body: PromoteRequest) -> AchievementResponse:
    achievement = db.get_achievement_by_id(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")
    if not achievement.get("notion_page_id"):
        raise HTTPException(status_code=400, detail="Achievement has not been promoted to Notion yet")
    if not os.getenv("NOTION_API_KEY"):
        raise HTTPException(status_code=503, detail="Notion API key not configured")

    screenshot_dir = SCREENSHOTS_DIR / str(achievement_id)
    screenshot_paths: list[Path] = []
    if screenshot_dir.exists():
        screenshot_paths = sorted(screenshot_dir.iterdir())

    try:
        notion_sync.update_notion_page(
            page_id=achievement["notion_page_id"],
            achievement=achievement,
            star_narrative={
                "situation": body.situation,
                "task": body.task,
                "action": body.action,
                "result": body.result,
            },
            screenshot_paths=screenshot_paths,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    db.set_notion_page_id(achievement_id, achievement["notion_page_id"])
    updated = db.get_achievement_by_id(achievement_id)
    assert updated is not None
    return AchievementResponse(**updated)


@app.post("/api/achievements/{achievement_id}/screenshots")
async def upload_screenshot(achievement_id: int, file: UploadFile) -> dict[str, str]:
    """Upload a screenshot for an achievement."""
    achievement = db.get_achievement_by_id(achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    screenshot_dir = SCREENSHOTS_DIR / str(achievement_id)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "screenshot.png"
    file_path = screenshot_dir / filename
    content = await file.read()
    file_path.write_bytes(content)

    return {"filename": filename, "path": str(file_path)}


# --- CSV Export ---


@app.get("/api/achievements/export")
def export_achievements() -> StreamingResponse:
    achievements = db.get_achievements(include_archived=True)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "title", "company", "situation", "task",
        "action", "result", "tags", "created_at", "archived", "notion_page_id",
    ])
    for a in achievements:
        writer.writerow([
            a["id"], a["title"] or "", a["company"] or "",
            a["situation"], a["task"] or "", a["action"], a["result"] or "",
            "|".join(a["tags"]), a["created_at"],
            "yes" if a["archived"] else "no", a["notion_page_id"] or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=achievements.csv"},
    )


# --- Static files (frontend) ---

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
