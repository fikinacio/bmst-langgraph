#!/bin/sh
set -e

if [ "$FLY_PROCESS_GROUP" = "scheduler" ]; then
    exec python -m src.scheduler.cron
else
    exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080
fi
