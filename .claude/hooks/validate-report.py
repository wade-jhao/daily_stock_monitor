#!/usr/bin/env python3
"""
Pre-send validation hook for Slack messages.
Checks for common quality issues before allowing message delivery.
Reads hook input from stdin, outputs JSON to stdout.
"""

import json
import sys
import re


def validate_message(message: str) -> list[str]:
    """Validate a Slack message and return list of issues found."""
    issues = []

    # 1. Stock code validation: 群聯 must be 8299, not 8046
    if "群聯" in message:
        pattern = r"群聯[^)]*\(8046\)|群聯[^)]*8046"
        if re.search(pattern, message):
            issues.append("群聯代碼錯誤：使用了 8046（南電），應為 8299")
    # 1b. Reverse check: 南電 must be 8046, not 8299
    if "南電" in message:
        pattern = r"南電[^)]*\(8299\)|南電[^)]*8299"
        if re.search(pattern, message):
            issues.append("南電代碼錯誤：使用了 8299（群聯），應為 8046")

    # 2. Fuzzy number detection in critical data positions
    fuzzy_patterns = [
        (r"指數[：:]\s*~", "指數使用了模糊符號 ~"),
        (r"[±+\-]\s*~", "漲跌幅使用了模糊符號 ~"),
        (r"匯率[：:]\s*~", "匯率使用了模糊符號 ~"),
        (r"\d+\.X", "出現半精確數字 X（如 31.X）"),
        (r"YY\.X", "出現模板佔位符 YY.X"),
        (r"XX,XXX", "出現未填入的模板 XX,XXX"),
        (r"±X\.XX%", "出現未填入的模板 ±X.XX%"),
    ]
    for pattern, desc in fuzzy_patterns:
        if re.search(pattern, message):
            issues.append(f"模糊數字：{desc}")

    # 2b. Fuzzy description words in data contexts
    fuzzy_word_patterns = [
        (r"[指數漲跌幅匯率成交][：:][^，。\n]*約\s*\d", "關鍵數據使用「約」"),
        (r"[指數漲跌幅匯率成交][：:][^，。\n]*大約", "關鍵數據使用「大約」"),
        (r"\d+\s*[點元億%]\s*左右", "數據使用「左右」"),
        (r"\d+\s*[點元億%]\s*附近", "數據使用「附近」"),
        (r"接近\s*\d+\s*[點元億%]", "數據使用「接近」"),
    ]
    for pattern, desc in fuzzy_word_patterns:
        if re.search(pattern, message):
            issues.append(f"模糊描述：{desc}")

    # 2c. Unfilled template placeholders
    template_patterns = [
        (r"YYYY-MM-DD", "未填入日期模板 YYYY-MM-DD"),
        (r"\[族群\]|\[簡述\]|\[判讀\]|\[事件\]", "未填入方括號模板佔位符"),
    ]
    for pattern, desc in template_patterns:
        if re.search(pattern, message):
            issues.append(f"模板未填：{desc}")

    # 3. Empty shell section detection
    empty_patterns = [
        "尚未取得",
        "待補",
        "待確認",
        "資料截至蒐集時未取得",
    ]
    for pat in empty_patterns:
        if pat in message:
            issues.append(f"空殼區段：包含「{pat}」")

    # 4. Banned investment advice language
    advice_patterns = [
        "建議買進",
        "建議賣出",
        "強烈推薦",
        "保證獲利",
    ]
    for pat in advice_patterns:
        if pat in message:
            issues.append(f"投資建議用語：包含「{pat}」")

    # 5. Wrong Slack format detection
    if "**" in message:
        issues.append("格式錯誤：使用了雙星號 **（應用單星號 *）")
    if re.search(r"^#+\s", message, re.MULTILINE):
        issues.append("格式錯誤：使用了 # 標題語法（Slack 不支援）")
    if "<b>" in message or "<br>" in message or "<p>" in message:
        issues.append("格式錯誤：使用了 HTML 標籤")
    # 5b. Markdown link format (should be Slack format <URL|text>)
    if re.search(r"\[.+?\]\(https?://.+?\)", message):
        issues.append("格式錯誤：使用了 Markdown 連結 [text](url)（應用 <url|text>）")

    # 6. Self-calculated exchange rate detection
    if "換算" in message and "匯率" in message:
        issues.append("匯率可能為自行推算（偵測到「換算」+「匯率」）")
    if "ADR" in message and "反推" in message:
        issues.append("匯率可能用 ADR 反推（禁止行為）")

    # 7. Message length check (Slack limit ~4000, our target 3500)
    if len(message) > 3500:
        issues.append(f"訊息過長：{len(message)} 字（上限 3500）")

    return issues


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # If no input or invalid JSON, allow through
        sys.exit(0)

    # Extract the message content from the tool input
    tool_input = hook_input.get("tool_input", {})
    message = tool_input.get("message", "") or tool_input.get("text", "")

    if not message:
        # No message content to validate
        sys.exit(0)

    issues = validate_message(message)

    if issues:
        # Output denial with reasons
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"報告品質檢查未通過（{len(issues)} 項問題）：\n"
                    + "\n".join(f"  - {issue}" for issue in issues)
                    + "\n\n請修正後重新發送。"
                ),
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    else:
        # All checks passed, allow send
        sys.exit(0)


if __name__ == "__main__":
    main()
