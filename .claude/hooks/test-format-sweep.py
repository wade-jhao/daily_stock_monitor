#!/usr/bin/env python3
"""Repo format sweep: no lone *text* may survive in files whose content is sent to Slack.

The Slack connector consumes STANDARD MARKDOWN, so a lone *text* renders as
italic, not bold. Message templates live inside the routine prompts and the
ground-truth fallback messages — whatever markup they carry is copied verbatim
into the report, so they must use **text**.

Also checks table placement: tables render visually in Slack but do NOT appear
in the retrievable message text (verified 2026-09-15), which would blind the
Step 0.3 cross-routine memory layer. Messages 1 and 3 of the US routine are the
memory layer's read-back targets, so tables are confined to message 2.

Run: python3 .claude/hooks/test-format-sweep.py
Exit 0 = clean, 1 = issues found.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Files whose content is copied verbatim into Slack messages.
TARGETS = [
    "routines/01_premarket_tw.md",
    "routines/02_postmarket_tw.md",
    "routines/03_premarket_us.md",
    ".claude/skills/ground-truth-tw.md",
    ".claude/skills/ground-truth-us.md",
]

# A line teaching the rule is allowed to show the wrong form as an example.
ALLOW_MARKERS = ("會渲染成斜體", "會變斜體")

ASCII_PUNCT = ")]}>\"'.,;:!?%"
BOLD_SPAN = re.compile(r"\*\*([^*\n]+)\*\*")
PLACEHOLDER_ONLY = re.compile(r"\[[^\]]*\]")
# ASCII-only boundary guards, never \w: in Python \w matches CJK ideographs,
# which would hide "這是*重點*說明" from this check. The guards exist only to
# avoid matching a*b*c / 2*3*4.
LONE_STAR = re.compile(r"(?<![*A-Za-z0-9_])\*(?!\*)[^*\n]{1,80}(?<!\*)\*(?![*A-Za-z0-9_])")
OVER_STAR = re.compile(r"\*{3,}")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
MSG_MARKER = re.compile(r"【第\s*([0-9])\s*則")


def scan_lone_stars() -> list[str]:
    issues = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            issues.append(f"{rel}: MISSING")
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if any(m in line for m in ALLOW_MARKERS):
                continue
            hit = LONE_STAR.search(line)
            if hit:
                issues.append(f"{rel}:{i}: 單星號 {hit.group()[:40]}")
            over = OVER_STAR.search(line)
            if over:
                issues.append(f"{rel}:{i}: 過度轉換 {over.group()}")
    return issues


def scan_table_placement() -> list[str]:
    """Tables must not appear in messages 1 or 3 — those are read back by the memory layer."""
    issues = []
    p = ROOT / "routines/03_premarket_us.md"
    current = None
    for i, line in enumerate(p.read_text().splitlines(), 1):
        marker = MSG_MARKER.search(line)
        if marker:
            current = marker.group(1)
        if TABLE_ROW.match(line) and current in ("1", "3"):
            issues.append(
                f"routines/03_premarket_us.md:{i}: 第 {current} 則不得使用表格（記憶層回讀目標）"
            )
    return issues


def scan_broken_bold() -> list[str]:
    """Bold ending in ASCII punctuation followed by a full-width char never renders.

    CommonMark right-flanking: a closing ** preceded by ASCII punctuation and
    followed by a non-ASCII character is not a valid closing delimiter, so the
    asterisks survive verbatim in the message (verified end-to-end 2026-09-16,
    7 controlled cases). Safe form: move the code out — **台積電**(2330).
    """
    issues = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if any(m in line for m in ALLOW_MARKERS):
                continue
            for m in BOLD_SPAN.finditer(line):
                content = m.group(1)
                # A bold span that is ENTIRELY one [placeholder] is a template
                # slot: the model substitutes real text (**[族群]** → **航運**),
                # so the rendered bold never ends in ASCII punctuation. Only the
                # template scanner skips these — validate-report.py, which sees
                # the real outgoing message, deliberately does NOT whitelist.
                if PLACEHOLDER_ONLY.fullmatch(content):
                    continue
                if content[-1] not in ASCII_PUNCT:
                    continue
                nxt = line[m.end():m.end() + 1]
                if nxt and not nxt.isspace() and ord(nxt) > 127:
                    issues.append(
                        f"{rel}:{i}: 粗體收尾為半形標點且緊接全形字元，不會渲染 "
                        f"{m.group(0)[:36]} → 改寫為 **名稱**(代號)"
                    )
    return issues


def main() -> int:
    issues = scan_lone_stars() + scan_table_placement() + scan_broken_bold()
    for x in issues:
        print(f"FAIL {x}")
    print(f"\n{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
