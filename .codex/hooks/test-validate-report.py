#!/usr/bin/env python3
"""Self-test for validate-report.py. Run: python3 .claude/hooks/test-validate-report.py"""
import importlib.util
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("vr", HERE / "validate-report.py")
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)

CASES = [
    # (name, message, expect_hard, expect_soft)
    ("標準粗體通過",        "**大盤總覽**\n加權指數：45,862.52（-0.70%）", False, False),
    ("單星號應警告",        "*大盤總覽*\n加權指數：45,862.52", False, True),
    ("標準連結不再誤判",    "延伸閱讀：[Fed 決策](https://example.com/fed)", False, False),
    ("Slack 連結仍通過",    "延伸閱讀：<https://example.com/fed|Fed 決策>", False, False),
    ("# 標題應提醒",        "# 台股摘要\n內文", False, True),
    ("HTML 應警告",         "<b>粗體</b>", False, True),
    ("約+金額應警告",       "TSM ADR：前一交易日約 $433", False, True),
    ("百分比區間應警告",    "標普期：-0.5%～-0.6%", False, True),
    ("小跌應警告",          "道瓊期：小跌（相對抗跌）", False, True),
    ("群聯代碼錯誤擋下",    "記憶體：群聯(8046) 走強", True, False),
    ("南電代碼錯誤擋下",    "載板：南電(8299) 走強", True, False),
    ("模板未填擋下",        "加權指數：XX,XXX", True, False),
    ("日期模板擋下",        "**【台股摘要 YYYY-MM-DD】**", True, False),
    ("方括號模板擋下",      "強勢族群：[族群]", True, False),
    ("匯率自算擋下",        "以 ADR 換算後匯率為 31.5", True, False),
    ("粗體半形括號收尾應警告", "**台積電 (2330)**：走強", False, True),
    ("粗體方括號收尾應警告",   "**[方括號]**：內容", False, True),
    ("代號移出粗體應通過",     "**台積電**(2330)：走強", False, False),
    ("粗體後接空格應通過",     "**CRDO (Credo)** 動向轉強", False, False),
    ("單星號緊貼漢字應警告",   "這是*重點*說明", False, True),
    ("單星號夾在漢字間應警告", "外資*買超*張數創高", False, True),
    ("乘法運算不應誤判",       "計算式 2*3*4 的結果", False, False),
    ("英數字間星號不應誤判",   "檔名 a*b*c 的樣式", False, False),
]


# 跨則去重案例：(name, message, expect_warning)
DEDUP_CASES = [
    (
        "去重-第1則無警告",
        "加權指數 45,862 收黑 -0.70%；成交 3,210 億元。"
        "台積電 +1.25%，NVDA $140.50，TSM ADR $433.00。",
        False,
    ),
    (
        "去重-第2則重複5項應警告",
        "延續前述：加權指數 45,862（-0.70%）、成交 3,210 億元，"
        "台積電 +1.25%，NVDA 報 $140.50。",
        True,
    ),
    (
        "去重-第3則僅重複1項不警告",
        "加權指數 45,862 之外，本則聚焦櫃買 9,999 與外資期貨部位。",
        False,
    ),
]


def run_dedup():
    """Cross-message dedup detection: warn only when >= DEDUP_THRESHOLD facts repeat."""
    failed = 0
    try:
        os.remove(vr.FACTS_FILE)
    except FileNotFoundError:
        pass

    for name, msg, want_warn in DEDUP_CASES:
        issues = vr.check_duplication(msg)
        got_warn = any("跨則重複" in i for i in issues)
        if got_warn != want_warn:
            failed += 1
            print(f"FAIL {name}\n     issues={issues}")
        else:
            print(f"ok   {name}")

    try:
        os.remove(vr.FACTS_FILE)
    except FileNotFoundError:
        pass
    return failed


def run():
    failed = 0
    for name, msg, want_hard, want_soft in CASES:
        hard, soft = vr.validate_message(msg)
        ok = bool(hard) == want_hard and bool(soft) == want_soft
        if not ok:
            failed += 1
            print(f"FAIL {name}\n     hard={hard}\n     soft={soft}")
        else:
            print(f"ok   {name}")

    failed += run_dedup()
    total = len(CASES) + len(DEDUP_CASES)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
