# 執行計畫（修訂 r1）：daily-monitor-v4

- **任務代號**：`daily-monitor-v4`｜**分支**：`feature/daily-monitor-v4`｜**基準**：`4cc34c5`
- **前一版計畫**：`docs/plans/2026-09-15-daily-monitor-v4.md`（C1–C6 已完成）
- **本版目標**：(A) 落實 D2 修訂（表格只留在第 2 則的報價格子）；(B) 修補 C2 未完成的模板轉換
- **執行方式**：`/dev-implement` 逐步執行。每步為 2–5 分鐘的單一動作。

## 迭代回饋（第 1 輪｜觸發：自動偵測 → 使用者裁決）

- **未達標關卡**：驗證 / 驗收項 7 — 表格未進入可回讀文字
- **根因**：決策錯誤（D2 前提來自工具說明，單一來源、未經端對端驗證）
- **重跑必須改變的事**：依 F9/F10 重新收斂表格用法（混合制）
- **已嘗試且無效**：① 以工具說明當作表格支援依據 ② 以單一讀取格式判斷
- **本版新增根因**：設計缺陷 — 原設計的變更清單只寫「反轉三個 routine 的**格式段**」，
  漏掉 routine 內的**訊息模板本身**。模板是模型抄寫報告時照著寫的內容，未轉換等於格式修復只做了兩成。

---

## Commit C7 — 常駐格式掃描器（先 RED）

> 為何需要它：上一輪驗收項 6 用 `grep "單星號"` 檢查，只能抓到警語文字，
> 抓不到實際的單星號用法 —— 159 處缺陷就是這樣溜過去的。改用可執行的掃描器。

### 步驟 7.1 建立 `.claude/hooks/test-format-sweep.py`

```python
#!/usr/bin/env python3
"""Repo format sweep: no lone *text* may survive in files whose content is sent to Slack.

Run: python3 .claude/hooks/test-format-sweep.py
Exit 0 = clean, 1 = residual single-asterisk emphasis found.
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

LONE_STAR = re.compile(r"(?<![*\w])\*(?!\*)[^*\n]{1,80}(?<!\*)\*(?![*\w])")
OVER_STAR = re.compile(r"\*{3,}")
# Tables are allowed ONLY inside message 2 of the US routine (see D2 revision).
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
            if LONE_STAR.search(line):
                issues.append(f"{rel}:{i}: 單星號 {LONE_STAR.search(line).group()[:40]}")
            if OVER_STAR.search(line):
                issues.append(f"{rel}:{i}: 過度轉換 {OVER_STAR.search(line).group()}")
    return issues


def scan_table_placement() -> list[str]:
    """Tables must not appear in messages 1 or 3 — those are read back by the memory layer."""
    issues = []
    p = ROOT / "routines/03_premarket_us.md"
    current = None
    for i, line in enumerate(p.read_text().splitlines(), 1):
        m = MSG_MARKER.search(line)
        if m:
            current = m.group(1)
        if TABLE_ROW.match(line) and current in ("1", "3"):
            issues.append(f"routines/03_premarket_us.md:{i}: 第 {current} 則不得使用表格（記憶層回讀目標）")
    return issues


def main() -> int:
    issues = scan_lone_stars() + scan_table_placement()
    for x in issues:
        print(f"FAIL {x}")
    print(f"\n{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
```

### 步驟 7.2 執行，預期 FAIL
```bash
python3 .claude/hooks/test-format-sweep.py; echo "exit=$?"
```
預期：約 **159 個 FAIL**（routines 157 + ground-truth 2），`exit=1`。
把完整輸出寫入 `<evidence>/c7-red.txt`。

### 步驟 7.3 提交掃描器（尚未修復，測試為紅）
```bash
git add .claude/hooks/test-format-sweep.py
git commit -m "test: 新增常駐格式掃描器（目前為紅，暴露 159 處未轉換的單星號）"
```

---

## Commit C8 — 模板單星號全面轉換

### 步驟 8.1 執行機械轉換

一次性腳本（不入版控，於 `/tmp` 執行）：

```python
import pathlib, re
ROOT = pathlib.Path("/Users/wadejhao/Documents/daily_stock_monitor")
TARGETS = ["routines/01_premarket_tw.md","routines/02_postmarket_tw.md",
           "routines/03_premarket_us.md",".claude/skills/ground-truth-tw.md",
           ".claude/skills/ground-truth-us.md"]
ALLOW = ("會渲染成斜體", "會變斜體")
PAT = re.compile(r"(?<![*\w])\*(?!\*)([^*\n]{1,80})(?<!\*)\*(?![*\w])")
for rel in TARGETS:
    p = ROOT / rel
    out, n = [], 0
    for line in p.read_text().splitlines():
        if any(m in line for m in ALLOW):
            out.append(line); continue
        new, k = PAT.subn(r"**\1**", line)
        out.append(new); n += k
    p.write_text("\n".join(out) + "\n")
    print(f"{rel}: {n} 處轉換")
```

預期輸出：`01` 30 處、`02` 51 處、`03` 73 處、`ground-truth-tw` 1 處、`ground-truth-us` 1 處。

### 步驟 8.2 執行掃描器，預期 GREEN
```bash
python3 .claude/hooks/test-format-sweep.py; echo "exit=$?"
```
預期：`0 issue(s)`、`exit=0`（表格位置檢查此時仍應為 0，因傳導鏈表格在第 2 則）。
輸出寫入 `<evidence>/c8-green.txt`。

### 步驟 8.3 過度轉換與遺漏檢查
```bash
grep -c '\*\*' routines/01_premarket_tw.md routines/02_postmarket_tw.md routines/03_premarket_us.md
grep -n '\*\*\*' routines/*.md .claude/skills/ground-truth-*.md || echo "  PASS 無三連星號"
```
預期：無 `***`；雙星號行數較轉換前顯著增加。

### 步驟 8.4 人工抽查 3 處
用 `sed -n` 印出 `routines/03_premarket_us.md` 的 155、232、340 行附近各 3 行，
確認轉換結果語意正確（標題變粗體，未破壞 `━━` 分隔線或 emoji）。

### 步驟 8.5 提交
```bash
git add routines/01_premarket_tw.md routines/02_postmarket_tw.md routines/03_premarket_us.md \
        .claude/skills/ground-truth-tw.md .claude/skills/ground-truth-us.md
git commit -m "fix: 轉換訊息模板殘留的 159 處單星號（C2 僅完成格式規範段）"
```

---

## Commit C9 — D2 修訂：表格只留報價格子

### 步驟 9.1 傳導鏈表格回退為條列
`routines/03_premarket_us.md` 第 333–338 行（`**━━ 美股 → 台股傳導鏈 ━━**` 之下的表格）改為：

```
📍 **傳導鏈 1**：[美股事件] → [傳導邏輯，20 字內] → [台股族群 + 個股代碼]
📍 **傳導鏈 2**：[美股事件] → [傳導邏輯] → [台股族群 + 個股代碼]
📍 **傳導鏈 3**：[美股事件] → [傳導邏輯] → [台股族群 + 個股代碼]
```

理由（寫進該段註記）：傳導鏈是記憶層最該繼承的內容，表格不進入可回讀文字。

### 步驟 9.2 在 routines/03 格式段新增表格位置規則
`routines/03_premarket_us.md` 格式段（約 434 行）的「表格」那行後面追加：

```
⚠️ 表格會在 Slack 視覺呈現，但**不會進入可回讀的訊息文字**（實測 2026-09-15）。
   因此表格僅限第 2 則的報價格子（MAG 7、半導體）使用；
   第 1 則與第 3 則為第 0.3 步記憶層的回讀目標，一律不得使用表格。
```

### 步驟 9.3 quality-gate-us 新增檢查項
`.claude/skills/quality-gate-us.md` 軟門檻追加第 13 項：
```markdown
13. □ 表格僅出現在第 2 則（報價格子）；第 1、3 則無 pipe 表格（表格不進入可回讀文字，會使記憶層失明）
```

### 步驟 9.4 三份總則補註記
`CLAUDE.md`、`AGENTS.md`、`.claude/CLAUDE.md` 的格式段，在「表格」該行後補一句：
> 表格會視覺呈現但不進入可回讀文字，勿用於需被下一個 routine 回讀的段落。

`AGENTS.md` 依既有方式由 `CLAUDE.md` 機械產生：
```bash
sed -e '1s/.*/# Daily Stock Monitor - AGENTS.md/' -e 's/Claude Code/Codex/g' CLAUDE.md > AGENTS.md
```

### 步驟 9.5 執行掃描器（含表格位置檢查）
```bash
python3 .claude/hooks/test-format-sweep.py; echo "exit=$?"
python3 .claude/hooks/test-validate-report.py | tail -2
```
預期：掃描器 `0 issue(s)`；validate-report 仍 `18/18 passed`（回歸）。

### 步驟 9.6 提交
```bash
git add routines/03_premarket_us.md .claude/skills/quality-gate-us.md CLAUDE.md .claude/CLAUDE.md
git commit -m "fix: D2 修訂 — 傳導鏈回退條列，表格僅限第 2 則報價格子"
```
（`AGENTS.md` 依既有決定維持未追蹤，僅在磁碟同步。）

---

## Commit C10 — 同步 Codex 副本

```bash
cp .claude/hooks/*.py .codex/hooks/
for f in .claude/hooks/*.py; do diff -q "$f" ".codex/hooks/$(basename $f)" || echo "DIFF $f"; done
git add .codex 2>/dev/null || true   # 預期不執行：.codex 維持未追蹤
```
`.codex/` 維持未追蹤 → 本 commit 僅在磁碟同步，不產生 commit（同 C6）。

---

## 驗收（交由 /dev-verify）

1. `python3 .claude/hooks/test-format-sweep.py` → `0 issue(s)`、exit 0
2. `python3 .claude/hooks/test-validate-report.py` → `18/18 passed`（回歸）
3. `grep -n '\*\*\*' routines/*.md .claude/skills/ground-truth-*.md` → 無輸出（無過度轉換）
4. `routines/03` 第 1、3 則無 pipe 表格；第 2 則仍有 MAG 7 與半導體兩張表
5. 傳導鏈區段為條列格式，不含 `|`
6. `.codex/hooks` 與 `.claude/hooks` byte-identical
7. `AGENTS.md` ≡ `CLAUDE.md`（sed 還原後 diff 無輸出）
8. **不需重跑端對端 Slack 測試** —— 粗體、斜體、連結三項已於第 1 輪證實
   （`https://sysfeather.slack.com/archives/D05965JHW8H/p1789468399376569`）；
   本輪只改星號數量與表格位置，未引入新的格式元素種類
