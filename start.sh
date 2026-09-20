#!/usr/bin/env bash
# Render only runs one start command per service, so this launches the
# MCP server in the background first (same as running "python server.py"
# yourself locally), waits a moment for it to be ready, then runs the
# FastAPI app in the foreground - Render tracks that as "the" process.

python server.py &
sleep 3
exec uvicorn app:app --host 0.0.0.0 --port $PORT
