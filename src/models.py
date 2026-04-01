"""Pydantic models for request/response validation."""

from pydantic import BaseModel


class AchievementCreate(BaseModel):
    title: str | None = None
    situation: str
    action: str
    result: str | None = None
    tags: list[str] = []


class AchievementUpdate(BaseModel):
    title: str | None = None
    situation: str | None = None
    action: str | None = None
    result: str | None = None
    tags: list[str] | None = None


class AchievementResponse(BaseModel):
    id: int
    title: str | None
    situation: str
    action: str
    result: str | None
    tags: list[str]
    created_at: str
    updated_at: str
    archived: bool
    notion_page_id: str | None


class TagSuggestRequest(BaseModel):
    situation: str
    action: str
    result: str | None = None


class TagSuggestResponse(BaseModel):
    suggested_tags: list[str]


class TitleSuggestResponse(BaseModel):
    suggested_title: str | None = None


class TagWithCount(BaseModel):
    tag: str
    count: int


class PromoteRequest(BaseModel):
    situation: str
    task: str
    action: str
    result: str
