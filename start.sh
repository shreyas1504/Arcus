#!/bin/bash
# Start Pulse backend
cd "$(dirname "$0")"
python -m uvicorn backend.main:app --reload --port 8000
