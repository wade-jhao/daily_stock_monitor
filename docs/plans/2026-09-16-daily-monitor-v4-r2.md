# 執行計畫（修訂 r2）：daily-monitor-v4

- **任務代號**：`daily-monitor-v4`｜**分支**：`feature/daily-monitor-v4`｜**基準**：`ec92f0e`
- **前版計畫**：`2026-09-15-daily-monitor-v4.md`（C1–C6）、`2026-09-15-daily-monitor-v4-r1.md`（C7–C10）
- **本版目標**：修復「粗體以半形標點收尾 + 緊接全形字元 → 渲染失敗」缺陷類別
- **執行方式**：`/dev-implement` 逐步執行

## 迭代回饋（第 2 輪｜觸發：自動）

- **未達標關卡**：驗證 / 端對端 — 粗體收尾為 ASCII 標點時未渲染
- **根因分類**：設計缺陷 — 機械轉換規則未考慮 CommonMark flanking delimiter 限制
- **已嘗試且無效**：① 工具說明當依據（表格）② 單一讀取格式判斷 ③ `grep "單星號"` 當驗收
  ④ 以「未引入新元素」推論可略過端對端 ⑤ 假設問題出在條列符號（對照實驗已排除）
- **重跑必須改變的事**：修模板 + **加 hook 攔截**（模型自由寫作，只修模板不夠）+ 加掃描器檢查 + 寫入格式規範

## 已實測確立的規則（2026-09-16，7 組對照）

| 粗體內容收尾 | 緊接字元 | 結果 |
|---|---|---|
| 半形 `)` | 全形 `：` | ❌ `**台積電 (2330)**：` |
| 半形 `)` | 全形 `，` | ❌ |
| 半形 `)`（無內部空格） | 全形 `：` | ❌ `**台積電(2330)**：` |
| 半形 `)` | **半形空格** | ✅ `**CRDO (Credo)** 動向：` |
| 漢字 | 全形 `：` | ✅ `**台積電**(2330)：` |
| 全形 `）` | 全形 `：` | ✅ `**台積電（2330）**：` |

**規則**：收尾 `**` 前為 ASCII 標點、後為非 ASCII 字元時，不構成合法收尾定界符 → 粗體失效。
**採用修法**：代號／括號內容一律移出粗體 → `**名稱**(代號)`。統一適用台股與美股，且粗體以字母或漢字收尾，最穩健。

---

## Commit C11 — 掃描器與 hook 檢查（先 RED）

### 步驟 11.1 在 `test-format-sweep.py` 新增檢查函式

在 `scan_table_placement()` 之後新增 `scan_broken_bold()`，並於 `main()` 併入 issues：

```python
ASCII_PUNCT = ")]}>\"'.,;:!?%"
BOLD_SPAN = re.compile(r"\*\*([^*\n]+)\*\*")


def scan_broken_bold() -> list[str]:
    """Bold ending in ASCII punctuation followed by a full-width char never renders.

    CommonMark right-flanking: a closing ** preceded by ASCII punctuation and
    followed by a non-ASCII character is not a valid closing delimiter, so the
    asterisks survive verbatim in the message (verified 2026-09-16, 7 cases).
    Safe form: move the code out of the bold — **台積電**(2330).
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
                if m.group(1)[-1] not in ASCII_PUNCT:
                    continue
                nxt = line[m.end():m.end() + 1]
                if nxt and not nxt.isspace() and ord(nxt) > 127:
                    issues.append(
                        f"{rel}:{i}: 粗體收尾為半形標點且緊接全形字元，不會渲染 "
                        f"{m.group(0)[:36]} → 改寫為 **名稱**(代號)"
                    )
    return issues
```

### 步驟 11.2 在 `validate-report.py` 新增送出前檢查

於 `# 5. Format validation` 區塊末端追加（SOFT，與相鄰格式規則同層級）：

```python
    for m in re.finditer(r"\*\*([^*\n]+)\*\*", message):
        if m.group(1)[-1] in ")]}>\"'.,;:!?%":
            nxt = message[m.end():m.end() + 1]
            if nxt and not nxt.isspace() and ord(nxt) > 127:
                soft.append(
                    f"格式錯誤：粗體 {m.group(0)[:24]} 以半形標點收尾又緊接全形字元，"
                    "星號會原樣外露；請改寫為 **名稱**(代號)"
                )
                break
```

### 步驟 11.3 在 `test-validate-report.py` 新增 4 個案例

```python
    ("粗體半形括號收尾應警告", "**台積電 (2330)**：走強", False, True),
    ("粗體方括號收尾應警告",   "**[方括號]**：內容", False, True),
    ("代號移出粗體應通過",     "**台積電**(2330)：走強", False, False),
    ("粗體後接空格應通過",     "**CRDO (Credo)** 動向轉強", False, False),
```

### 步驟 11.4 執行兩支測試，預期 FAIL
```bash
python3 .claude/hooks/test-format-sweep.py; echo "sweep exit=$?"
python3 .claude/hooks/test-validate-report.py | tail -3
```
預期：sweep 報 **27 個 FAIL**（01:7、02:3、03:17）、exit 1；
validate-report 的前兩個新案例 FAIL（尚未實作檢查）→ `20/22 passed`。
輸出寫入 `<evidence>/c11-red.txt`。

### 步驟 11.5 提交（測試為紅）
```bash
git add .claude/hooks/test-format-sweep.py .claude/hooks/test-validate-report.py .claude/hooks/validate-report.py
git commit -m "test: 新增粗體收尾檢查（掃描器 27 FAIL，暴露渲染失效的粗體）"
```
> 註：`validate-report.py` 的檢查在 11.2 已實作，故 validate-report 測試此時應已轉綠；
> 掃描器仍為紅（模板尚未修）。若 validate-report 未全綠，先修至全綠再提交。

---

## Commit C12 — 模板修正（代號移出粗體）

### 步驟 12.1 執行機械轉換

一次性腳本（於 `/tmp` 執行，不入版控）：

```python
import pathlib, re
ROOT = pathlib.Path("/Users/wadejhao/Documents/daily_stock_monitor")
TARGETS = ["routines/01_premarket_tw.md","routines/02_postmarket_tw.md","routines/03_premarket_us.md"]
ALLOW = ("會渲染成斜體", "會變斜體")
# **名稱 (內容)** → **名稱**(內容)   /   **名稱 [內容]** → **名稱**[內容]
PAT = re.compile(r"\*\*([^*\n]+?)\s*([(\[][^)\]\n]*[)\]])\*\*")
for rel in TARGETS:
    p = ROOT / rel
    out, n = [], 0
    for line in p.read_text().splitlines():
        if any(m in line for m in ALLOW):
            out.append(line); continue
        new, k = PAT.subn(r"**\1**\2", line)
        out.append(new); n += k
    p.write_text("\n".join(out) + "\n")
    print(f"{rel}: {n} 處轉換")
```

⚠️ 此 regex 不處理「整個粗體就是一個方括號佔位符」的情況（如 `**[族群]**`），
因為沒有可保留的「名稱」部分。這些在步驟 12.2 手動處理。

### 步驟 12.2 手動處理純佔位符粗體

以下形式無法機械轉換，需改寫模板結構，讓**代號位置明確落在粗體外**：

- `routines/01:216,218` `- **[族群/個股 + 股號]**：` → `- **[族群/個股]**([股號])：`
- `routines/01:222-224` `**[族群]**：` → 檢查上下文，若後接全形冒號則改為 `**[族群]**` + 半形空格，
  或比照 216 改為 `**[族群]**([代表股])`
- `routines/02:214` `- **[族群/個股]**：` → 同 01:216
- `routines/02:249` `**[判讀結果]**` → 後接行尾，無需改
- 其餘 `**[族群]** (+X.XX%)：` 形式後接半形空格，已安全，不動

逐行以 `sed -n` 確認上下文後再改，勿批次替換。

### 步驟 12.3 執行掃描器，預期 GREEN
```bash
python3 .claude/hooks/test-format-sweep.py; echo "exit=$?"
```
預期：`0 issue(s)`、exit 0。輸出寫入 `<evidence>/c12-green.txt`。

### 步驟 12.4 不變量檢查
```bash
for f in routines/01_premarket_tw.md routines/02_postmarket_tw.md routines/03_premarket_us.md; do
  diff <(git show HEAD:"$f" | tr -d '*() []') <(tr -d '*() []' < "$f") >/dev/null \
    && echo "PASS $f — 僅星號與括號位置改變" || echo "CHECK $f"
done
```
`CHECK` 的檔案需人工看 diff 確認只有預期的結構調整。

### 步驟 12.5 回歸
```bash
python3 .claude/hooks/test-validate-report.py | tail -2
```
預期：`22/22 passed`。

### 步驟 12.6 提交
```bash
git add routines/01_premarket_tw.md routines/02_postmarket_tw.md routines/03_premarket_us.md
git commit -m "fix: 代號移出粗體，修復 42 處會渲染失效的粗體"
```

---

## Commit C13 — 格式規範明列規則

### 步驟 13.1 三份總則
`CLAUDE.md`、`.claude/CLAUDE.md` 的格式段，在粗體那行後追加：

> ⚠️ 粗體**不得以半形標點收尾**（`)` `]` `%` 等）後緊接全形字元 —— 星號會原樣外露。
> 標準寫法：代號放在粗體外 → `**台積電**(2330)`、`**CRDO**(Credo)`。
> （若後面接的是半形空格則無此問題，但統一採用上述寫法以免出錯。）

`AGENTS.md` 由 `CLAUDE.md` 機械產生：
```bash
sed -e '1s/.*/# Daily Stock Monitor - AGENTS.md/' -e 's/Claude Code/Codex/g' CLAUDE.md > AGENTS.md
```

### 步驟 13.2 三個 routine 格式段
各自的「粗體：**文字**（雙星號）」那行後追加同一條規則（精簡版一行）。

### 步驟 13.3 兩份 quality-gate
`quality-gate-tw.md` 與 `quality-gate-us.md` 的軟門檻第 7 項後追加：
```markdown
7b. □ 粗體未以半形標點收尾後緊接全形字元（`**台積電 (2330)**：` ✗ → `**台積電**(2330)：` ✓）
```

### 步驟 13.4 驗證與提交
```bash
python3 .claude/hooks/test-format-sweep.py; echo "exit=$?"
python3 .claude/hooks/test-validate-report.py | tail -2
diff <(sed -e '1s/.*/# Daily Stock Monitor - CLAUDE.md/' -e 's/Codex/Claude Code/g' AGENTS.md) CLAUDE.md && echo "AGENTS 同步"
git add CLAUDE.md .claude/CLAUDE.md routines/*.md .claude/skills/quality-gate-*.md
git commit -m "docs: 格式規範明列粗體收尾規則"
```

---

## Commit C14 — 同步 Codex 副本
```bash
cp .claude/hooks/*.py .codex/hooks/
for f in .claude/hooks/*.py; do diff -q "$f" ".codex/hooks/$(basename $f)" || echo "DIFF"; done
```
`.codex/` 維持未追蹤 → 不產生 commit。

---

## 驗收（交由 /dev-verify）

1. `test-format-sweep.py` → `0 issue(s)`、exit 0
2. `test-validate-report.py` → `22/22 passed`
3. 反例測試：臨時在模板插入 `**測試 (123)**：中文`，掃描器必須 FAIL；還原後回綠
4. 反例測試：對 hook 送入 `**台積電 (2330)**：走強`，必須回 SOFT 警告
5. `.codex/hooks` 與 `.claude/hooks` byte-identical；`AGENTS.md` ≡ `CLAUDE.md`
6. **端對端（必做，不得以推論略過）**：發一則 DM，內容涵蓋修正後的三種實際形式 ——
   `**台積電**(2330)：`、`**CRDO**(Credo)：`、`- **重電/電網**(1519)：`，
   回讀確認全部儲存為 `*…*`（Slack bold），無 `**` 殘留。
   ⚠️ 前四輪的教訓：不得以「未引入新元素種類」推論略過此步。
