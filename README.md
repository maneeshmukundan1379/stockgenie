# 📈 Stock Assistant

An AI-powered stock chatbot — a **single Python (FastAPI) app**. It serves a chat
web page (`static/index.html`) and a `/analyze` endpoint that runs the OpenAI agent
pipeline (entity extraction → live market data → analysis).

The UI is one self-contained HTML file using React + Tailwind from a CDN, so there
is **no separate frontend, no Node, and no build step**.

## Project layout

```
stock_assistant_api.py     FastAPI: /analyze + /health, serves the chat UI
stock_orchestrator.py      Routing + orchestration
stock_agents.py            Agent definitions
stock_tools.py             Data/news/sector tools
static/index.html          The chat UI (React + Tailwind via CDN)
Dockerfile                 Single-stage Python image
railway.json               Railway deploy config
```

## Environment variables

Copy `.env.example` to `.env` (local) or set these in Railway → Variables:

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Powers all agents |
| `ALPHA_VANTAGE_API_KEY` | optional | Market data/news (falls back to Yahoo Finance) |

## Run locally

```bash
pip install -r requirements.txt
python3 run.py
# open http://localhost:8000
```

## Deploy to Railway

1. Push this repo to GitHub.
2. Railway → **New Project → Deploy from GitHub repo** (it uses `railway.json` +
   `Dockerfile` — one service).
3. Add the environment variables above under the service's **Variables** tab.
4. Railway sets `$PORT` automatically; the server binds to it.

> ⚠️ Never commit `.env`. Rotate any keys that may have been exposed.
