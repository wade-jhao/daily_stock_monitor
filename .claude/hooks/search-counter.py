#!/usr/bin/env python3
"""
Post-WebSearch hook to track search count.
Warns Claude when approaching the search limit.
Reads hook input from stdin, outputs feedback to stdout.
"""

import json
import os
import sys

# Search limits per routine type (detected from message context)
SEARCH_LIMITS = {
    "premarket_tw": 7,
    "postmarket_tw": 8,
    "premarket_us": 9,
    "default": 8,
}

COUNTER_FILE = "/tmp/claude_search_counter.json"


def get_counter() -> dict:
    """Read current search counter from temp file."""
    try:
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"count": 0, "session_id": ""}


def save_counter(data: dict):
    """Save search counter to temp file."""
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    # Get or initialize counter
    counter = get_counter()

    # Detect session (reset counter for new sessions)
    session_id = hook_input.get("session_id", "unknown")
    if counter.get("session_id") != session_id:
        counter = {"count": 0, "session_id": session_id}

    # Increment
    counter["count"] += 1
    save_counter(counter)

    count = counter["count"]
    limit = SEARCH_LIMITS["default"]

    # Determine which routine based on tool output content
    tool_output = str(hook_input.get("tool_output", ""))
    if "盤前" in tool_output and "台股" in tool_output:
        limit = SEARCH_LIMITS["premarket_tw"]
    elif "盤後" in tool_output:
        limit = SEARCH_LIMITS["postmarket_tw"]
    elif "美股" in tool_output or "pre-market" in tool_output.lower():
        limit = SEARCH_LIMITS["premarket_us"]

    # Warn when approaching limit
    if count >= limit:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "message": (
                    f"⚠️ 搜尋次數已達上限 {count}/{limit}！"
                    f"請立即停止搜尋，進入訊息撰寫階段。"
                ),
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    elif count >= limit - 1:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "message": (
                    f"⚠️ 搜尋次數 {count}/{limit}，僅剩 {limit - count} 次。"
                    f"請評估是否需要最後一次搜尋。"
                ),
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    else:
        # Under limit, no warning needed
        sys.exit(0)


if __name__ == "__main__":
    main()
