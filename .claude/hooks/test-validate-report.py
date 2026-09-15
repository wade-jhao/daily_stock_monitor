#!/usr/bin/env python3
"""Self-test for validate-report.py. Run: python3 .claude/hooks/test-validate-report.py"""
import importlib.util
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
]


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
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
