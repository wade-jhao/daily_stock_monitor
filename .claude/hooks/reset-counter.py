#!/usr/bin/env python3
"""
SessionStart hook: reset search counter and detect routine type to set limit.
"""

import json
import sys

COUNTER_FILE = "/tmp/claude_search_counter.json"

# Limits per routine type
LIMITS = {
    "premarket_tw": 7,
    "postmarket_tw": 8,
    "premarket_us": 9,
}


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    # Try to detect routine type from the session prompt
    prompt = str(hook_input.get("prompt", ""))

    if "盤前" in prompt and "台股" in prompt and "美股" not in prompt:
        limit = LIMITS["premarket_tw"]
    elif "盤後" in prompt:
        limit = LIMITS["postmarket_tw"]
    elif "美股" in prompt or "MAG 7" in prompt:
        limit = LIMITS["premarket_us"]
    else:
        limit = 8  # default

    counter = {"count": 0, "limit": limit}
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f)

    sys.exit(0)


if __name__ == "__main__":
    main()
