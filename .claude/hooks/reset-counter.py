#!/usr/bin/env python3
"""
SessionStart hook: reset the search counter and clear cross-message dedup state.
"""

import json
import os
import sys

SEARCH_LIMIT = 9
COUNTER_FILE = "/tmp/claude_search_counter.json"
FACTS_FILE = "/tmp/claude_report_facts.json"

# Routine-type detection was removed: the SessionStart payload carries no user
# prompt (session_id / transcript_path / cwd / hook_event_name / source only),
# so detection always fell through to the default. All routines now share one
# limit; per-routine discipline lives in each routine prompt instead.


def main():
    try:
        json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        pass

    counter = {"count": 0, "limit": SEARCH_LIMIT}
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f)

    try:
        os.remove(FACTS_FILE)
    except FileNotFoundError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
