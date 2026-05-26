#!/usr/bin/env python3
"""
PreToolUse hook for WebFetch: BLOCKS requests to known 403 domains.
Prevents wasting execution time on domains that always return HTTP 403.
"""

import json
import sys
from urllib.parse import urlparse

BLOCKED_DOMAINS = [
    "twse.com.tw",       # includes www / rwd / mops subdomains
    "goodinfo.tw",
    "histock.tw",
    "sinotrade.com.tw",
    "wantgoo.com",
    "fubon-ebrokerdj.fbs.com.tw",
]


def is_blocked(url: str) -> str | None:
    """Return the matched blocked domain, or None if allowed."""
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return None
    for domain in BLOCKED_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return domain
    return None


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    url = tool_input.get("url", "")

    if not url:
        sys.exit(0)

    blocked = is_blocked(url)
    if blocked:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"封鎖網域：{blocked} 永遠回傳 HTTP 403，"
                    f"禁止 WebFetch。請改用 WebSearch 從搜尋摘要擷取資訊。"
                ),
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
