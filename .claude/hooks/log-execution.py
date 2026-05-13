#!/usr/bin/env python3
"""
Stop hook: log execution summary to file for historical tracking.
Captures timestamp, search count, and completion status.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

LOG_FILE = "execution-log.jsonl"
COUNTER_FILE = "/tmp/claude_search_counter.json"

def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    # Read search count
    search_count = 0
    try:
        with open(COUNTER_FILE, "r") as f:
            counter = json.load(f)
            search_count = counter.get("count", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Taiwan time
    tw_tz = timezone(timedelta(hours=8))
    now = datetime.now(tw_tz)

    # Log entry
    entry = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "search_count": search_count,
        "stop_reason": hook_input.get("stop_reason", "unknown"),
    }

    # Append to log file
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Clean up counter file
    try:
        os.remove(COUNTER_FILE)
    except FileNotFoundError:
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
