import json
import sys

import duckdb
from mcp.server.fastmcp import FastMCP

from data import load_match_events, get_competitions
from schema import COLUMN_GUIDE

if sys.platform == "win32":
    import asyncio
    # avoids a noisy but harmless ConnectionResetError that Windows'
    # default asyncio event loop logs when an HTTP connection closes
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

mcp = FastMCP("football-analytics")


@mcp.resource("statsbomb://competitions")
def competitions() -> str:
    """List of competitions and seasons available to query."""
    return json.dumps(get_competitions())


@mcp.resource("statsbomb://schema")
def schema_guide() -> str:
    """How the events table is structured and how to compute common metrics from it."""
    return COLUMN_GUIDE


@mcp.tool()
def run_query(match_id: int, sql: str) -> list[dict]:
    """
    Run a read-only SQL query against a match's events.

    The table is called "events", one row per event. Column names with
    dots need double quotes, e.g. "shot.statsbomb_xg". Results are capped
    at 200 rows - use GROUP BY / ORDER BY / LIMIT to narrow down what you
    need instead of expecting every raw event back.
    """
    if not sql.strip().lower().startswith("select"):
        raise ValueError("only SELECT queries are allowed")

    events = load_match_events(match_id)
    con = duckdb.connect()
    con.register("events", events)

    try:
        result = con.execute(sql).df()
    except duckdb.Error as e:
        # surface a clean message instead of DuckDB's raw traceback, so
        # the agent can read it and try a corrected query
        raise ValueError(f"SQL error: {e}") from e

    if len(result) > 200:
        result = result.head(200)

    return result.to_dict(orient="records")


@mcp.tool()
def build_chart(rows: list[dict], chart_type: str, x_field: str, y_field: str, title: str = "") -> dict:
    """
    Turn query results (from run_query) into a chart spec the frontend can render.

    chart_type must be "bar" or "line". x_field and y_field must be keys
    present in the rows, e.g. x_field="player", y_field="xg".
    """
    if chart_type not in ("bar", "line"):
        raise ValueError('chart_type must be "bar" or "line"')
    if not rows:
        raise ValueError("no rows to chart")
    if x_field not in rows[0] or y_field not in rows[0]:
        raise ValueError(f"rows don't have fields {x_field!r} / {y_field!r}")

    return {
        "type": chart_type,
        "title": title,
        "x": [row[x_field] for row in rows],
        "y": [row[y_field] for row in rows],
        "x_label": x_field,
        "y_label": y_field,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")