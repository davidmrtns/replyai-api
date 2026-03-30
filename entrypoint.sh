#!/bin/sh
./scripts/generate_database.sh && exec uvicorn main:app --host 0.0.0.0 --port 8000
