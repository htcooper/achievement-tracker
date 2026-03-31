"""Tests for the API endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src import database as db
from src.app import app


@pytest.fixture(autouse=True)
def tmp_db(tmp_path: Path) -> None:
    """Use a temporary database for each test."""
    test_db = tmp_path / "test.db"
    screenshots = tmp_path / "screenshots"
    with (
        patch.object(db, "DB_PATH", test_db),
        patch.object(db, "DB_DIR", tmp_path),
        patch("src.app.SCREENSHOTS_DIR", screenshots),
    ):
        db.init_db()
        screenshots.mkdir(parents=True, exist_ok=True)
        yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestCreateAchievement:
    def test_create(self, client: TestClient) -> None:
        resp = client.post(
            "/api/achievements",
            json={
                "situation": "Team needed help",
                "action": "I helped",
                "result": "Problem solved",
                "tags": ["leadership"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["situation"] == "Team needed help"
        assert data["tags"] == ["leadership"]
        assert data["archived"] is False

    def test_create_minimal(self, client: TestClient) -> None:
        resp = client.post(
            "/api/achievements",
            json={
                "situation": "Context",
                "action": "Did it",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["result"] is None

    def test_create_missing_fields(self, client: TestClient) -> None:
        resp = client.post("/api/achievements", json={"situation": "S"})
        assert resp.status_code == 422


class TestListAchievements:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/achievements")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_items(self, client: TestClient) -> None:
        client.post("/api/achievements", json={"situation": "S1", "action": "A1"})
        client.post("/api/achievements", json={"situation": "S2", "action": "A2"})
        resp = client.get("/api/achievements")
        assert len(resp.json()) == 2

    def test_search(self, client: TestClient) -> None:
        client.post(
            "/api/achievements", json={"situation": "Auth migration", "action": "A1"}
        )
        client.post(
            "/api/achievements", json={"situation": "Code review", "action": "A2"}
        )
        resp = client.get("/api/achievements?q=migration")
        assert len(resp.json()) == 1

    def test_filter_by_tag(self, client: TestClient) -> None:
        client.post(
            "/api/achievements",
            json={"situation": "S1", "action": "A1", "tags": ["leadership"]},
        )
        client.post(
            "/api/achievements",
            json={"situation": "S2", "action": "A2", "tags": ["technical"]},
        )
        resp = client.get("/api/achievements?tags=leadership")
        assert len(resp.json()) == 1


class TestUpdateAchievement:
    def test_update(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/achievements", json={"situation": "Old", "action": "A"}
        )
        aid = create_resp.json()["id"]
        resp = client.put(f"/api/achievements/{aid}", json={"situation": "New"})
        assert resp.status_code == 200
        assert resp.json()["situation"] == "New"

    def test_update_not_found(self, client: TestClient) -> None:
        resp = client.put("/api/achievements/999", json={"situation": "X"})
        assert resp.status_code == 404


class TestDeleteAchievement:
    def test_delete(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/achievements", json={"situation": "S", "action": "A"}
        )
        aid = create_resp.json()["id"]
        resp = client.delete(f"/api/achievements/{aid}")
        assert resp.status_code == 200
        assert client.get(f"/api/achievements/{aid}").status_code == 404


class TestArchive:
    def test_toggle_archive(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/achievements", json={"situation": "S", "action": "A"}
        )
        aid = create_resp.json()["id"]

        resp = client.patch(f"/api/achievements/{aid}/archive")
        assert resp.status_code == 200
        assert resp.json()["archived"] is True

        resp = client.patch(f"/api/achievements/{aid}/archive")
        assert resp.json()["archived"] is False


class TestTags:
    def test_get_tags(self, client: TestClient) -> None:
        client.post(
            "/api/achievements",
            json={"situation": "S", "action": "A", "tags": ["leadership", "technical"]},
        )
        client.post(
            "/api/achievements",
            json={"situation": "S", "action": "A", "tags": ["leadership"]},
        )
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        tags = resp.json()
        assert tags[0]["tag"] == "leadership"
        assert tags[0]["count"] == 2


class TestFeatures:
    def test_features_no_keys(self, client: TestClient) -> None:
        with patch.dict("os.environ", {}, clear=True):
            resp = client.get("/api/config/features")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ai_tags"] is False
            assert data["notion"] is False


class TestSuggestTags:
    def test_suggest_no_api_key(self, client: TestClient) -> None:
        with patch("src.tag_suggester.is_configured", return_value=False):
            resp = client.post(
                "/api/suggest-tags",
                json={
                    "situation": "S",
                    "action": "A",
                },
            )
            assert resp.status_code == 503

    def test_suggest_with_mock(self, client: TestClient) -> None:
        with (
            patch("src.tag_suggester.is_configured", return_value=True),
            patch(
                "src.tag_suggester.suggest_tags",
                return_value=["leadership", "mentoring"],
            ),
        ):
            resp = client.post(
                "/api/suggest-tags",
                json={
                    "situation": "Led a team",
                    "action": "Mentored juniors",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["suggested_tags"] == ["leadership", "mentoring"]
