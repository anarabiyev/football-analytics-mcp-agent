import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import build_agent, ask
from data import get_competitions, get_matches
from schema import AVAILABLE_METRICS

agent = None  # built once when the server starts, reused for every request

# simple per-visitor rate limit, to keep a public deployment from
# quietly burning through the OpenAI budget
RATE_LIMIT = 10             # max questions
RATE_LIMIT_WINDOW = 3600    # per this many seconds (1 hour)
_request_log = defaultdict(list)


def get_client_ip(request: Request) -> str:
    # Render (and most hosts) put the app behind a proxy, so the real
    # visitor's IP shows up in this header instead of request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def check_rate_limit(ip: str):
    now = time.time()
    recent = [t for t in _request_log[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(recent) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded - max {RATE_LIMIT} questions per hour. Try again later.",
        )
    recent.append(now)
    _request_log[ip] = recent


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = await build_agent()  # connects to the MCP server, loads tools + schema
    yield
    # nothing to clean up when shutting down, for now


app = FastAPI(lifespan=lifespan)

# the frontend is a separate static file/origin, so the browser needs
# permission to call this API - fine to leave wide open for a hobby project
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    match_id: int
    session_id: str


@app.get("/metrics")
async def metrics_endpoint():
    return {"metrics": AVAILABLE_METRICS}


@app.get("/competitions")
async def competitions_endpoint():
    return get_competitions()


@app.get("/matches")
async def matches_endpoint(competition_id: int, season_id: int):
    return get_matches(competition_id, season_id)


@app.post("/ask")
async def ask_endpoint(payload: AskRequest, http_request: Request):
    check_rate_limit(get_client_ip(http_request))
    return await ask(agent, payload.question, payload.match_id, payload.session_id)