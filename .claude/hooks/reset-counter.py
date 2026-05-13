#!/usr/bin/env python3
"""
SessionStart hook: reset search counter for new session.
"""

import json
import os
import sys

COUNTER_FILE = "/tmp/claude_search_counter.json"

def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    session_id = hook_input.get("session_id", "unknown")

    counter = {"count": 0, "session_id": session_id}
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f)

    sys.exit(0)

if __name__ == "__main__":
    main()
