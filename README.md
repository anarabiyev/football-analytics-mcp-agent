# Football Analytics MCP Agent

Ask natural-language questions about football matches — "who had the most xG
in this match?", "top 10 players by passes" — and get an answer backed by
real SQL run against StatsBomb's open event data, with a chart when that
tells the story better than prose.

**Live demo:** https://football-analytics-mcp-agent.vercel.app/

## Why this exists

Most agent projects bake the "smart part" and the "tool part" into one app.
Here they're deliberately split: the SQL and charting tools are exposed
through an MCP (Model Context Protocol) server — a standalone service that
any MCP-compatible client could use, not just this one. The LangGraph agent
in this repo happens to be its client, but it doesn't have to be the only
one.

## How it works

1. Pick a match from the two-level dropdown (competition, then match) —
   both pulled live from StatsBomb's open dataset.
2. Ask a question. A LangGraph agent decides whether it has enough to
   answer, or needs to ask you something first.
3. If it needs data, it calls `run_query` over MCP, which runs the SQL it
   wrote against that match's events in DuckDB.
4. If the result is worth a chart, it calls `build_chart` — and the exact
   numbers from that tool call, not the model's retelling of them, are what
   get rendered.

`PROJECT_GUIDE.md` has a full, line-by-line walkthrough of every file if
you want the details.

## Stack

- **MCP** (official Python SDK) — the analytics engine's protocol
- **LangGraph** — the agent loop, structured output, session memory
- **OpenAI** (`gpt-4.1-mini`) — the model doing the reasoning
- **FastAPI** — the web API
- **DuckDB** — in-memory SQL over the event data
- **Vanilla JS + Chart.js** — the frontend, no build step
- Deployed on **Render** (backend) and **Vercel** (frontend)

## Running it locally

```bash
python -m venv venv
venv\Scripts\activate        # or: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add your OPENAI_API_KEY
```

Two terminals:

```bash
python server.py                          # the MCP server
uvicorn app:app --reload --port 8001      # the API
```

Then open `frontend/index.html` in a browser.

## Project structure

```
data.py       fetches + caches StatsBomb data
schema.py     what's queryable and how - for the frontend and the agent
server.py     the MCP server - tools and resources
agent.py      the LangGraph agent, an MCP client
app.py        FastAPI wrapper the frontend talks to
frontend/     the static UI
start.sh      combined start command for Render
```

## Honest limitations

- Rate-limited to 10 questions/hour per visitor, with a hard spend cap on
  the OpenAI account behind it — this is a portfolio project, not a funded
  product.
- Session memory and the events cache are in-memory only; both reset if the
  server restarts.
- Free-tier hosting means the backend can take 30-60s to wake up after
  sitting idle.
