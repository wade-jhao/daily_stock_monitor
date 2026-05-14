#!/usr/bin/env python3
"""
PreToolUse hook for WebSearch: BLOCKS searches that exceed the limit.
Must be PreToolUse to deny the tool call before it executes.
"""

import json
import sys

COUNTER_FILE = "/tmp/claude_search_counter.json"
DEFAULT_LIMIT = 8


def get_counter() -> dict:
    try:
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"count": 0}


def save_counter(data: dict):
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    counter = get_counter()
    count = counter.get("count", 0)
    limit = counter.get("limit", DEFAULT_LIMIT)

    # Increment before check (this search would be count+1)
    next_count = count + 1

    if next_count > limit:
        # BLOCK the search
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"搜尋次數已達上限 {count}/{limit}！"
                    f"禁止繼續搜尋，請立即進入訊息撰寫階段。"
                ),
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    else:
        # Allow and increment
        counter["count"] = next_count
        save_counter(counter)

        if next_count == limit:
            # Last allowed search - warn
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": (
                        f"⚠️ 這是最後一次搜尋 ({next_count}/{limit})，之後將被攔截。"
                    ),
                }
            }
            json.dump(result, sys.stdout, ensure_ascii=False)
        elif next_count == limit - 1:
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": (
                        f"搜尋次數 {next_count}/{limit}，僅剩 1 次。"
                    ),
                }
            }
            json.dump(result, sys.stdout, ensure_ascii=False)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
