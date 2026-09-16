#!/usr/bin/env python3
"""
Pre-send validation hook for Slack messages.
Checks for common quality issues before allowing message delivery.
Reads hook input from stdin, outputs JSON to stdout.
"""

import json
import sys
import re

FACTS_FILE = "/tmp/claude_report_facts.json"
DEDUP_THRESHOLD = 5


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
        (r"約\s*\$?[-+]?\d", "報價位使用「約」+ 數字"),
        (r"[-+]?\d+(?:\.\d+)?%\s*[～~]\s*[-+]?\d+(?:\.\d+)?%", "報價位使用百分比區間（如 -0.5%～-0.6%）"),
        (r"[：:]\s*小[漲跌]|微幅", "報價位使用「小漲/小跌/微幅」而非具體數字"),
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

    # 3b. Over-apologizing: too many "未取得/未能取得" disclaimers [SOFT]
    na_count = message.count("未取得") + message.count("未能取得")
    if na_count > 3:
        soft.append(
            f"過多缺口標註：「未取得/未能取得」出現 {na_count} 次"
            "（建議省略空區段，僅在結尾用 1 行彙整關鍵缺口）"
        )

    # 3c. Duplicated send trailer (inflates length) [SOFT]
    if message.count("已透過以下方式傳送") > 1:
        soft.append("傳送 trailer 重複出現（建議去重，避免訊息超長）")

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

    # 5. Format validation — the Slack connector consumes STANDARD MARKDOWN
    #    (**bold**, _italic_), NOT Slack mrkdwn. A lone *text* renders italic.
    if re.search(r"(?<![*\w])\*(?!\*)[^*\n]{1,80}(?<!\*)\*(?![*\w])", message):
        soft.append("格式錯誤：偵測到單星號 *文字*（會渲染成斜體）；粗體請用 **文字**")
    if re.search(r"^#{1,6}\s", message, re.MULTILINE):
        soft.append("格式提醒：本專案不使用 # 標題（connector 支援，但 Slack 字級跳動過大）")
    if "<b>" in message or "<br>" in message or "<p>" in message:
        soft.append("格式錯誤：使用了 HTML 標籤")

    # 5b. Bold ending in ASCII punctuation followed by a full-width character
    #     never renders: CommonMark right-flanking rejects that closing **, so
    #     the asterisks survive verbatim (verified end-to-end 2026-09-16).
    #     Safe form: move the code out of the bold — **台積電**(2330).
    for m in re.finditer(r"\*\*([^*\n]+)\*\*", message):
        if m.group(1)[-1] in ")]}>\"'.,;:!?%":
            nxt = message[m.end():m.end() + 1]
            if nxt and not nxt.isspace() and ord(nxt) > 127:
                soft.append(
                    f"格式錯誤：粗體 {m.group(0)[:24]} 以半形標點收尾又緊接全形字元，"
                    "星號會原樣外露；請改寫為 **名稱**(代號)"
                )
                break

    # 6. Self-calculated exchange rate detection [HARD]
    if "換算" in message and "匯率" in message:
        hard.append("匯率可能為自行推算（偵測到「換算」+「匯率」）")
    if "ADR" in message and "反推" in message:
        hard.append("匯率可能用 ADR 反推（禁止行為）")

    # 7. Message length check [SOFT]
    if len(message) > 3500:
        soft.append(f"訊息過長：{len(message)} 字（上限 3500）")

    return hard, soft


def _fact_tokens(message: str) -> set[str]:
    """Numeric tokens that identify a concrete fact (prices, changes, amounts)."""
    toks: set[str] = set()
    toks |= set(re.findall(r"[-+]?\d[\d,]*\.\d+%", message))     # -5.9%
    toks |= set(re.findall(r"\d{1,3}(?:,\d{3})+", message))       # 45,862
    toks |= set(re.findall(r"\$\d[\d,]*(?:\.\d+)?", message))     # $140
    return toks


def check_duplication(message: str) -> list[str]:
    """Warn when this message restates facts already sent earlier this session."""
    toks = _fact_tokens(message)
    try:
        with open(FACTS_FILE) as f:
            seen = set(json.load(f).get("tokens", []))
    except (FileNotFoundError, json.JSONDecodeError):
        seen = set()

    issues = []
    overlap = toks & seen
    if len(overlap) >= DEDUP_THRESHOLD:
        sample = "、".join(sorted(overlap)[:6])
        issues.append(
            f"跨則重複：本則有 {len(overlap)} 個數值與前則重複（{sample}…）；"
            "同一事實請只完整敘述一次，其餘則以 15 字內指涉"
        )

    try:
        with open(FACTS_FILE, "w") as f:
            json.dump({"tokens": sorted(seen | toks)}, f)
    except OSError:
        pass
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

    hard, soft = validate_message(message)
    if not hard:
        # Messages blocked by a hard gate are never sent, so they must not
        # pollute the "already seen facts" ledger.
        soft += check_duplication(message)

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
