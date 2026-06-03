#!/usr/bin/env python3
"""
Pre-send validation hook for Slack messages.
Checks for common quality issues before allowing message delivery.
Reads hook input from stdin, outputs JSON to stdout.
"""

import json
import sys
import re


def validate_message(message: str) -> tuple[list[str], list[str]]:
    """Validate a Slack message. Returns (hard_issues, soft_issues).
    Hard issues block sending; soft issues warn but allow."""
    hard = []
    soft = []

    # 1. Stock code validation: 群聯 must be 8299, not 8046 [HARD]
    if "群聯" in message:
        pattern = r"群聯[^)]*\(8046\)|群聯[^)]*8046"
        if re.search(pattern, message):
            hard.append("群聯代碼錯誤：使用了 8046（南電），應為 8299")
    # 1b. Reverse check: 南電 must be 8046, not 8299 [HARD]
    if "南電" in message:
        pattern = r"南電[^)]*\(8299\)|南電[^)]*8299"
        if re.search(pattern, message):
            hard.append("南電代碼錯誤：使用了 8299（群聯），應為 8046")

    # 2. Fuzzy number detection in critical data positions [HARD]
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
            hard.append(f"模糊數字：{desc}")

    # 2b. Fuzzy description words in data contexts [SOFT]
    fuzzy_word_patterns = [
        (r"[指數漲跌幅匯率成交][：:][^，。\n]*約\s*\d", "關鍵數據使用「約」"),
        (r"[指數漲跌幅匯率成交][：:][^，。\n]*大約", "關鍵數據使用「大約」"),
        (r"\d+\s*[點元億%]\s*左右", "數據使用「左右」"),
        (r"\d+\s*[點元億%]\s*附近", "數據使用「附近」"),
        (r"接近\s*\d+\s*[點元億%]", "數據使用「接近」"),
    ]
    for pattern, desc in fuzzy_word_patterns:
        if re.search(pattern, message):
            soft.append(f"模糊描述：{desc}")

    # 2c. Unfilled template placeholders [HARD]
    template_patterns = [
        (r"YYYY-MM-DD", "未填入日期模板 YYYY-MM-DD"),
        (r"\[族群\]|\[簡述\]|\[判讀\]|\[事件\]", "未填入方括號模板佔位符"),
    ]
    for pattern, desc in template_patterns:
        if re.search(pattern, message):
            hard.append(f"模板未填：{desc}")

    # 3. Empty shell section detection [SOFT]
    empty_patterns = [
        "尚未取得",
        "待補",
        "資料截至蒐集時未取得",
    ]
    for pat in empty_patterns:
        if pat in message:
            soft.append(f"空殼區段：包含「{pat}」")

    # 4. Banned investment advice language [SOFT]
    advice_patterns = [
        "建議買進",
        "建議賣出",
        "強烈推薦",
        "保證獲利",
    ]
    for pat in advice_patterns:
        if pat in message:
            soft.append(f"投資建議用語：包含「{pat}」")

    # 5. Wrong Slack format detection [SOFT]
    if "**" in message:
        soft.append("格式錯誤：使用了雙星號 **（應用單星號 *）")
    if re.search(r"^#+\s", message, re.MULTILINE):
        soft.append("格式錯誤：使用了 # 標題語法（Slack 不支援）")
    if "<b>" in message or "<br>" in message or "<p>" in message:
        soft.append("格式錯誤：使用了 HTML 標籤")
    # 5b. Markdown link format (should be Slack format <URL|text>)
    if re.search(r"\[.+?\]\(https?://.+?\)", message):
        soft.append("格式錯誤：使用了 Markdown 連結 [text](url)（應用 <url|text>）")

    # 6. Self-calculated exchange rate detection [HARD]
    if "換算" in message and "匯率" in message:
        hard.append("匯率可能為自行推算（偵測到「換算」+「匯率」）")
    if "ADR" in message and "反推" in message:
        hard.append("匯率可能用 ADR 反推（禁止行為）")

    # 7. Message length check [SOFT]
    if len(message) > 3500:
        soft.append(f"訊息過長：{len(message)} 字（上限 3500）")

    return hard, soft


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

    hard, soft = validate_message(message)

    if hard:
        # Hard issues: BLOCK sending
        reason = f"🔴 品質硬門檻未通過（{len(hard)} 項）：\n"
        reason += "\n".join(f"  - {i}" for i in hard)
        if soft:
            reason += f"\n\n🟡 另有軟性問題（{len(soft)} 項）：\n"
            reason += "\n".join(f"  - {i}" for i in soft)
        reason += "\n\n請修正 🔴 項目後重新發送。"
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    elif soft:
        # Soft issues: WARN but allow sending
        reason = f"🟡 品質軟性提醒（{len(soft)} 項，允許發送）：\n"
        reason += "\n".join(f"  - {i}" for i in soft)
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            }
        }
        json.dump(result, sys.stdout, ensure_ascii=False)
    else:
        # All checks passed
        sys.exit(0)


if __name__ == "__main__":
    main()
