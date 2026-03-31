# Achievement Tracker — Setup Guide

## Prerequisites

- Python 3.11 or higher

## 1. Install Dependencies

```bash
pip install -e .
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework for the API |
| `uvicorn` | ASGI server to run the app |
| `openai` | AI-powered tag suggestions |
| `python-dotenv` | Load API keys from `.env` file |
| `python-multipart` | Handle file uploads (screenshots) |

For development (optional):

```bash
pip install -e ".[dev]"
```

## 2. Configure API Keys

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your keys. Both are optional — the app works without them, just with reduced features:

```
OPENAI_API_KEY=your-openai-api-key
NOTION_API_KEY=your-notion-integration-secret
NOTION_DATABASE_ID=your-notion-database-id
```

### Setting up OpenAI (for tag suggestions)

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Paste it as `OPENAI_API_KEY` in your `.env`

### Setting up Notion (for promoting achievements)

#### Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"New integration"**
3. Name it "Achievement Tracker"
4. Select your workspace
5. Copy the **Internal Integration Secret** — this is your `NOTION_API_KEY`

#### Create the Notion Database

1. In Notion, create a new **full-page database** (type `/database` and select "Database - Full page")
2. Rename the default "Name" column to **"Title"** by clicking on the column header
3. Add the following properties by clicking **+** on the right side of the column headers:

| Property Name | Type | Notes |
|---|---|---|
| Title | Title | Rename the default "Name" column |
| Situation | Text | |
| Task | Text | |
| Action | Text | |
| Result | Text | |
| Tags | Multi-select | Change the type from "Text" to "Multi-select" |
| Date | Date | Change the type from "Text" to "Date" |

4. Connect the integration: on the database page, click **"..."** (top right) → **"Connections"** → find "Achievement Tracker" and add it

#### Get the Database ID

1. Open the database page in your browser
2. The URL looks like: `https://www.notion.so/yourworkspace/Page-Title-abc123def456...?v=...`
3. The database ID is the 32-character hex string at the end of the page name (before `?v=`)
4. Paste it as `NOTION_DATABASE_ID` in your `.env`

## 3. Run the App

```bash
python launcher.py
```

This starts the server and opens your browser automatically. Press `Ctrl+C` to stop.

## Features

- **Add achievements** with Situation, Action, and Result fields
- **Tag achievements** with autocomplete from existing tags
- **AI tag suggestions** — click "Suggest Tags" to get AI-powered suggestions that reuse your existing tags
- **Search and filter** by keyword, tag, or date range
- **Monthly grouping** — achievements grouped by month, collapsible
- **Archive** — hide old achievements without deleting them
- **Promote to Notion** — write up a full STAR story and send it to your Notion database
- **WhisprFlow compatible** — dictate into any text field

## Editing the AI Prompt

The tag suggestion prompt is stored in `src/prompts/tag_suggestions.txt`. Edit this file to customize how AI suggests tags — no code changes needed.
