"""Tests for the database layer."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src import database as db


@pytest.fixture(autouse=True)
def tmp_db(tmp_path: Path) -> None:
    """Use a temporary database for each test."""
    test_db = tmp_path / "test.db"
    with patch.object(db, "DB_PATH", test_db), patch.object(db, "DB_DIR", tmp_path):
        db.init_db()
        yield


class TestAddAndGet:
    def test_add_achievement(self) -> None:
        result = db.add_achievement(
            situation="Team needed auth migration",
            action="Led the migration to new provider",
            result="Reduced login latency by 40%",
            tags=["leadership", "technical"],
            title="Auth migration",
        )
        assert result["id"] == 1
        assert result["title"] == "Auth migration"
        assert result["situation"] == "Team needed auth migration"
        assert result["action"] == "Led the migration to new provider"
        assert result["result"] == "Reduced login latency by 40%"
        assert result["tags"] == ["leadership", "technical"]
        assert result["archived"] is False
        assert result["notion_page_id"] is None

    def test_add_achievement_no_title(self) -> None:
        result = db.add_achievement(
            situation="Context",
            action="Did something",
        )
        assert result["title"] is None
        assert result["result"] is None
        assert result["tags"] == []

    def test_get_by_id(self) -> None:
        created = db.add_achievement(situation="S", action="A")
        fetched = db.get_achievement_by_id(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_by_id_not_found(self) -> None:
        assert db.get_achievement_by_id(999) is None

    def test_get_all(self) -> None:
        db.add_achievement(situation="S1", action="A1")
        db.add_achievement(situation="S2", action="A2")
        results = db.get_achievements()
        assert len(results) == 2


class TestUpdate:
    def test_update_situation(self) -> None:
        created = db.add_achievement(situation="Old", action="A")
        updated = db.update_achievement(created["id"], situation="New")
        assert updated is not None
        assert updated["situation"] == "New"
        assert updated["action"] == "A"

    def test_update_tags(self) -> None:
        created = db.add_achievement(situation="S", action="A", tags=["old"])
        updated = db.update_achievement(created["id"], tags=["new1", "new2"])
        assert updated is not None
        assert updated["tags"] == ["new1", "new2"]

    def test_update_title(self) -> None:
        created = db.add_achievement(situation="S", action="A")
        updated = db.update_achievement(created["id"], title="New Title")
        assert updated is not None
        assert updated["title"] == "New Title"

    def test_update_not_found(self) -> None:
        assert db.update_achievement(999, situation="X") is None


class TestDelete:
    def test_delete(self) -> None:
        created = db.add_achievement(situation="S", action="A")
        assert db.delete_achievement(created["id"]) is True
        assert db.get_achievement_by_id(created["id"]) is None

    def test_delete_not_found(self) -> None:
        assert db.delete_achievement(999) is False


class TestArchive:
    def test_toggle_archive(self) -> None:
        created = db.add_achievement(situation="S", action="A")
        assert created["archived"] is False

        toggled = db.toggle_archive(created["id"])
        assert toggled is not None
        assert toggled["archived"] is True

        toggled_back = db.toggle_archive(created["id"])
        assert toggled_back is not None
        assert toggled_back["archived"] is False

    def test_archived_hidden_by_default(self) -> None:
        db.add_achievement(situation="S1", action="A1")
        a2 = db.add_achievement(situation="S2", action="A2")
        db.toggle_archive(a2["id"])

        results = db.get_achievements(include_archived=False)
        assert len(results) == 1
        assert results[0]["situation"] == "S1"

    def test_archived_included_when_requested(self) -> None:
        db.add_achievement(situation="S1", action="A1")
        a2 = db.add_achievement(situation="S2", action="A2")
        db.toggle_archive(a2["id"])

        results = db.get_achievements(include_archived=True)
        assert len(results) == 2


class TestTags:
    def test_get_all_tags(self) -> None:
        db.add_achievement(
            situation="S1", action="A1", tags=["leadership", "technical"]
        )
        db.add_achievement(
            situation="S2", action="A2", tags=["leadership", "mentoring"]
        )

        tags = db.get_all_tags()
        tag_dict = {t["tag"]: t["count"] for t in tags}
        assert tag_dict["leadership"] == 2
        assert tag_dict["technical"] == 1
        assert tag_dict["mentoring"] == 1

    def test_tags_exclude_archived(self) -> None:
        db.add_achievement(situation="S1", action="A1", tags=["active"])
        a2 = db.add_achievement(situation="S2", action="A2", tags=["archived-tag"])
        db.toggle_archive(a2["id"])

        tags = db.get_all_tags()
        tag_names = [t["tag"] for t in tags]
        assert "active" in tag_names
        assert "archived-tag" not in tag_names


class TestSearch:
    def test_search_by_query(self) -> None:
        db.add_achievement(situation="Auth migration", action="Led migration")
        db.add_achievement(situation="Code review", action="Reviewed PRs")

        results = db.search_achievements(query="migration")
        assert len(results) == 1
        assert results[0]["situation"] == "Auth migration"

    def test_search_by_tags(self) -> None:
        db.add_achievement(situation="S1", action="A1", tags=["leadership"])
        db.add_achievement(situation="S2", action="A2", tags=["technical"])

        results = db.search_achievements(tags=["leadership"])
        assert len(results) == 1
        assert results[0]["tags"] == ["leadership"]

    def test_search_excludes_archived(self) -> None:
        db.add_achievement(situation="Active", action="A1")
        a2 = db.add_achievement(situation="Archived", action="A2")
        db.toggle_archive(a2["id"])

        results = db.search_achievements()
        assert len(results) == 1


class TestNotionPageId:
    def test_set_notion_page_id(self) -> None:
        created = db.add_achievement(situation="S", action="A")
        db.set_notion_page_id(created["id"], "page-123")
        fetched = db.get_achievement_by_id(created["id"])
        assert fetched is not None
        assert fetched["notion_page_id"] == "page-123"
