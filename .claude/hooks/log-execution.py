#!/usr/bin/env python3
"""
Stop hook: output execution summary to stdout (no file writes).
Avoids git commit/push issues in remote routines.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

COUNTER_FILE = "/tmp/claude_search_counter.json"


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    # Read search count
    search_count = 0
    search_limit = 8
    try:
        with open(COUNTER_FILE, "r") as f:
            counter = json.load(f)
            search_count = counter.get("count", 0)
            search_limit = counter.get("limit", 8)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Clean up counter file
    try:
        os.remove(COUNTER_FILE)
    except FileNotFoundError:
        pass

    # Output summary as hook message (no file creation)
    tw_tz = timezone(timedelta(hours=8))
    now = datetime.now(tw_tz)

    over_limit = "OVER LIMIT" if search_count > search_limit else "OK"

    result = {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "message": (
                f"執行結束 {now.strftime('%H:%M')} | "
                f"搜尋 {search_count}/{search_limit} ({over_limit})"
            ),
        }
    }
    json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
