# Achievement Tracker — Build Tasks

- [x] Project scaffolding (git init, pyproject.toml, .env.example, directory structure)
- [x] Database layer (src/database.py — SQLite CRUD, search, archive, tags)
- [x] Pydantic models (src/models.py)
- [x] AI tag suggestions (src/tag_suggester.py + src/prompts/tag_suggestions.txt)
- [x] API routes (src/app.py — FastAPI endpoints)
- [x] Frontend (static/index.html, style.css, app.js — vanilla JS SPA)
- [x] Notion integration (src/notion_sync.py)
- [x] Launcher (launcher.py — starts server + opens browser)
- [x] Tests (39 tests passing, ruff clean)

## Review

- All 39 tests passing
- Ruff lint clean
- Black formatted
- Lifespan pattern used (no deprecation warnings)
