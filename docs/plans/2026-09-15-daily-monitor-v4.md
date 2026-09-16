# 執行計畫：daily-monitor-v4

- **任務代號**：`daily-monitor-v4`（ticketless，slug 於 assess 與使用者議定）
- **分支**：`feature/daily-monitor-v4`
- **目標**：讓 routine 的格式規則、搜尋上限機制與硬數據來源，與實際執行環境重新對齊。
- **執行方式**：`/dev-implement` 逐步執行本計畫。每步為 2–5 分鐘的單一動作。
- **校準決策**：D1 維持 3 則 + 去重規則｜D2 粗體斜體 + 表格、不用 `#`｜D3 統一 9 次｜D4 回退 WebSearch + 末行註記｜D5 Yahoo `^TWII` 為主｜D6 維持禁用 Bash

---

## Commit C1 — docs：提交本計畫

### 步驟 1.1 提交計畫檔
```bash
git add docs/plans/2026-09-15-daily-monitor-v4.md
git commit -m "docs: add daily-monitor-v4 execution plan"
```
預期：1 file changed。

---

## Commit C2 — 格式反轉（標準 Markdown）

> 依據：`slack_send_message` 工具說明「Message uses standard markdown (`**bold**`, `_italic_`)」。
> 現況 27 則輸出中 `_斜體_` 563 處 vs `*粗體*` 12 處 — 所有預期粗體都渲染成斜體。

### 步驟 2.1 先寫失敗測試
建立 `.claude/hooks/test-validate-report.py`（無測試框架，`python3` 直接執行）：

```python
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
```

### 步驟 2.2 執行測試，預期 FAIL
```bash
python3 .claude/hooks/test-validate-report.py
```
預期失敗項：`單星號應警告`、`標準連結不再誤判`、`約+金額應警告`、`百分比區間應警告`、`小跌應警告`。

### 步驟 2.3 反轉 validate-report.py 的格式檢查
檔案 `.claude/hooks/validate-report.py`，**取代第 98–107 行**（`# 5. Wrong Slack format detection` 整段）：

```python
    # 5. Format validation — the Slack connector consumes STANDARD MARKDOWN
    #    (**bold**, _italic_), NOT Slack mrkdwn. A lone *text* renders italic.
    if re.search(r"(?<![*\w])\*(?!\*)[^*\n]{1,80}(?<!\*)\*(?![*\w])", message):
        soft.append("格式錯誤：偵測到單星號 *文字*（會渲染成斜體）；粗體請用 **文字**")
    if re.search(r"^#{1,6}\s", message, re.MULTILINE):
        soft.append("格式提醒：本專案不使用 # 標題（connector 支援，但 Slack 字級跳動過大）")
    if "<b>" in message or "<br>" in message or "<p>" in message:
        soft.append("格式錯誤：使用了 HTML 標籤")
```

Markdown 連結規則（原 105–107 行）整段刪除 — `[文字](URL)` 現為建議寫法。

### 步驟 2.4 補強模糊數字偵測
同檔 `fuzzy_word_patterns`（第 45–51 行），在清單末端追加三條：

```python
        (r"約\s*\$?[-+]?\d", "報價位使用「約」+ 數字"),
        (r"[-+]?\d+(?:\.\d+)?%\s*[～~]\s*[-+]?\d+(?:\.\d+)?%", "報價位使用百分比區間（如 -0.5%～-0.6%）"),
        (r"[：:]\s*小[漲跌]|微幅", "報價位使用「小漲/小跌/微幅」而非具體數字"),
```

### 步驟 2.5 執行測試，預期全數 PASS
```bash
python3 .claude/hooks/test-validate-report.py
```
預期：`15/15 passed`。

### 步驟 2.6 反轉 CLAUDE.md 格式段
`CLAUDE.md` 第 202–209 行 `## Slack mrkdwn Format Reminder` 整段改為：

```markdown
## Slack 訊息格式（標準 Markdown）

Slack connector 接受的是**標準 Markdown**，不是 Slack mrkdwn。

- 粗體：`**文字**`（雙星號）— 單星號 `*文字*` 會渲染成斜體
- 斜體：`_文字_`
- 程式碼：`` `文字` ``
- 列表：`•` 開頭
- 連結：`[顯示文字](URL)`（`<URL|顯示文字>` 為既有可用寫法，不禁止但不推薦）
- 表格：標準 Markdown pipe 表格；結構性 `|` 不可 escape，僅儲存格內的字面 `|` 寫成 `\|`
- 禁止：HTML 標籤、`#`～`######` 標題（connector 支援，但 Slack 字級跳動過大）
```

### 步驟 2.7 反轉 AGENTS.md 同一段
`AGENTS.md` 第 202–209 行 — 內容與 `CLAUDE.md` 完全相同，套用同一份取代文字。

### 步驟 2.8 反轉 .claude/CLAUDE.md 規則 4
第 10 行改為：
```markdown
4. **格式**：標準 Markdown。粗體 `**文字**`（單星號 `*文字*` 會變斜體）、斜體 `_文字_`、表格可用。禁止 HTML、`#` 標題
```

### 步驟 2.9 反轉三個 routine 的格式段
- `routines/01_premarket_tw.md` 第 163–168 行：標題改「【Slack 訊息格式規範（標準 Markdown）】」，內文套用步驟 2.6 的規則
- `routines/03_premarket_us.md` 第 429–433 行：同上，保留「每則 3500 字內」
- `routines/02_postmarket_tw.md`：**原本沒有格式段**，在第 320 行（`【發送前品質門檻】`之前）新增同樣一段

### 步驟 2.10 反轉兩個 quality-gate 的第 7 項
`.claude/skills/quality-gate-tw.md` 與 `quality-gate-us.md` 第 19 行，皆改為：
```markdown
7. □ 標準 Markdown 正確：粗體 **文字**（勿用單星號 *文字*，會變斜體）；斜體 _文字_；連結 [文字](URL)；表格可用；禁 HTML、禁 # 標題
```

### 步驟 2.11 提交
```bash
git add -A && git commit -m "fix: 修正 Slack 格式規則為標準 Markdown（粗體從未生效）"
```

---

## Commit C3 — 搜尋上限統一 9 次

> 依據：`reset-counter.py` 讀 `hook_input["prompt"]`，但 SessionStart payload 無此欄位。
> 實測 `{"hook_event_name":"SessionStart","source":"startup"}` → `{"count":0,"limit":8}`，
> 導致美股 routine 宣告的 9 次上限從未生效（9/11、9/14 皆止於 8 次）。

### 步驟 3.1 簡化 reset-counter.py
移除 `LIMITS` dict 與整段 routine 類型偵測（第 12–35 行），改為固定值；同時清除去重追蹤檔：

```python
SEARCH_LIMIT = 9
COUNTER_FILE = "/tmp/claude_search_counter.json"
FACTS_FILE = "/tmp/claude_report_facts.json"

# Routine-type detection was removed: the SessionStart payload carries no user
# prompt (session_id / transcript_path / cwd / hook_event_name / source only),
# so detection always fell through to the default. All routines now share one
# limit; per-routine discipline lives in each routine prompt instead.
```
`main()` 寫入 `{"count": 0, "limit": SEARCH_LIMIT}`，並 `os.remove(FACTS_FILE)`（`FileNotFoundError` 忽略）。

### 步驟 3.2 對齊兩個 hook 的預設值
- `.claude/hooks/search-guard.py` 第 12 行：`DEFAULT_LIMIT = 8` → `9`
- `.claude/hooks/log-execution.py` 第 20、27 行：`search_limit = 8` / `counter.get("limit", 8)` → `9`

### 步驟 3.3 驗證 hook 行為
```bash
rm -f /tmp/claude_search_counter.json
echo '{"hook_event_name":"SessionStart","source":"startup"}' | python3 .claude/hooks/reset-counter.py
cat /tmp/claude_search_counter.json
```
預期：`{"count": 0, "limit": 9}`

```bash
for i in $(seq 1 10); do echo '{"tool_input":{"query":"x"}}' | python3 .claude/hooks/search-guard.py > /tmp/sg_$i.json; done
grep -l deny /tmp/sg_*.json
```
預期：僅 `/tmp/sg_10.json` 含 `deny`（第 9 次允許、第 10 次擋下）。

### 步驟 3.4 更新三個 routine 的宣告上限
- `routines/01_premarket_tw.md:60`：`7 次` → `9 次`
- `routines/02_postmarket_tw.md:49`：`8 次` → `9 次`
- `routines/03_premarket_us.md:45`：已是 `9 次`，不動

同時在各 routine 的搜尋清單末尾加註：
> 上限為 9 次，但**不必用滿** — 硬數據已由第 0.5 步 WebFetch 取得，搜尋只用於敘事、事件與法人新聞。

### 步驟 3.5 更新兩份總則與 quality-gate
- `CLAUDE.md:175` 與 `AGENTS.md:175`：`盤前 7 次、盤後 8 次、美股 9 次` → `三個 routine 一律 9 次`
- `.claude/skills/quality-gate-tw.md:24`（第 10 項）：`盤前 7／盤後 8` → `9`

### 步驟 3.6 提交
```bash
git add -A && git commit -m "fix: 統一搜尋上限為 9 次（routine 類型偵測掛錯 hook 事件，從未生效）"
```

---

## Commit C4 — 硬數據來源接管

> 依據實測：TAIFEX 外資 TX 淨 -83,223 口、Yahoo `TWD=X` 31.87、`^TWII` 45,511.49、TPEX openapi 200、
> `openapi.twse.com.tw` 回 200（非 403）。這些走 WebFetch，**不計搜尋次數**。

### 步驟 4.1 建立 .claude/skills/data-sources.md

frontmatter `name: data-sources`，`description: 硬數據固定端點清單與取數規則。WebFetch 取得，不計搜尋次數。`

內容須包含：

1. **共通取數指令**（寫進每個 WebFetch 的 prompt）：
   > 原樣回報數值，不得換算、不得四捨五入、不得推估。若頁面無該欄位，回答 `NOT_FOUND`。

2. **端點表**

| 用途 | URL | 取值欄位 | 狀態 |
|---|---|---|---|
| 加權指數 | `https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?range=5d&interval=1d` | `regularMarketPrice`、`chartPreviousClose` | ✅ 已實測 |
| USD/TWD | `https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?range=2d&interval=1d` | `regularMarketPrice` | ✅ 已實測 |
| 外資台指期 | `https://www.taifex.com.tw/cht/3/futContractsDate` | 臺股期貨 → 外資及陸資 → 未平倉多空淨額口數 | ✅ 已實測 |
| 櫃買指數 | `https://query1.finance.yahoo.com/v8/finance/chart/%5ETWOII?range=5d&interval=1d` | 同加權 | ⚠️ 步驟 4.6 待驗 |
| 美股期貨 | `.../chart/ES=F`、`NQ=F`、`YM=F` | 同上 | ⚠️ 步驟 4.6 待驗 |
| 費城半導體 | `.../chart/%5ESOX` | 同上 | ⚠️ 步驟 4.6 待驗 |
| 美股個股 | `.../chart/{TICKER}`（NVDA/TSLA/TSM/QQQ/VOO…） | 同上 | ⚠️ 步驟 4.6 待驗 |

3. **漲跌幅推導規則**：`(regularMarketPrice - chartPreviousClose) / chartPreviousClose`。
   兩者皆為交易所官方收盤價，相除屬算術，**不屬於「自行推算」禁令**（該禁令針對用 ADR 反推匯率）。

4. **回退規則（D4）**：任一端點失敗或回 `NOT_FOUND` → 走原本的 WebSearch 路徑，
   並在第 3 則末行「資料來源」欄註記，例：`_本日外資期貨改由媒體彙整；USD/TWD 改由搜尋摘要取得_`。
   **端點失敗不得中斷 routine，也不得列為硬門檻。**

5. **禁止事項**：不得對 `www.twse.com.tw`、`goodinfo.tw`、`histock.tw`、`sinotrade.com.tw`、
   `wantgoo.com`、`investing.com` 執行 WebFetch。`openapi.twse.com.tw` 為例外，允許。

### 步驟 4.2 改寫 01_premarket_tw.md 第 0.5 步
取代第 71–84 行。新內容要點：
- 標題改「【第 0.5 步：硬數據取得（WebFetch，不計搜尋次數）】」
- 引用 `⟹ 讀取 .claude/skills/data-sources.md`
- 取數項目：加權指數（Yahoo `^TWII`）、櫃買（`^TWOII`）、USD/TWD（`TWD=X`）、費半（`^SOX`）
- cnyes `https://www.cnyes.com/twstock/` 降為**備援**（D5）與成交值（億元）來源
- 保留既有的日期驗證（取得的交易日期應為前一交易日）
- 保留回退註記規則

### 步驟 4.3 改寫 02_postmarket_tw.md 第 0.5 步
取代第 89–102 行。與 4.2 相同，**外加**：
- 外資台指期（TAIFEX `futContractsDate`）→ 記為 `GT_FUT_FOREIGN`
- 美股期貨（`ES=F`/`NQ=F`/`YM=F`）供第 3 則夜盤聯動使用

### 步驟 4.4 改寫 03_premarket_us.md 第 0.5 步
取代第 53–64 行。取數項目：`YM=F`/`ES=F`/`NQ=F`/`^SOX`/`^VIX`/`DX-Y.NYB`/`NVDA`/`TSLA`/`TSM`/`QQQ`/`VOO`。
移除「此步驟的硬數據併入第 1 步前兩次搜尋取得」的舊敘述。

### 步驟 4.5 更新兩份 GT 登記表
`.claude/skills/ground-truth-tw.md`：
- `GT_INDEX` 來源改 Yahoo `^TWII`（cnyes 備援）
- `GT_CHANGE` 註明由官方收盤與前收相除
- 新增 `GT_OTC`（櫃買）、`GT_FUT_FOREIGN`（外資台指期淨口數，盤後專用）
- `GT_FX` 來源改 Yahoo `TWD=X`
- 硬門檻新增一條：**外資期貨方向與 `GT_FUT_FOREIGN` 正負相反 → BLOCK**
- 替代訊息中的 `_關鍵數據請直接查閱 cnyes.com_` 維持不變

`.claude/skills/ground-truth-us.md`：
- `GT_FUTURES_DOW/NQ` 來源改 Yahoo `YM=F`/`NQ=F`，新增 `GT_FUTURES_SPX`（`ES=F`）、`GT_SOX`（`^SOX`）
- `GT_NVDA`/`GT_TSLA` 來源改 `chart/NVDA`、`chart/TSLA`
- 替代訊息中的 `investing.com` 改為 `finance.yahoo.com`

### 步驟 4.6 驗證所有端點
```bash
for s in '%5ETWII' 'TWD=X' '%5ETWOII' 'ES=F' 'NQ=F' 'YM=F' '%5ESOX' '%5EVIX' 'NVDA' 'TSLA' 'TSM' 'QQQ' 'VOO'; do
  printf '%-10s ' "$s"
  curl -s --max-time 15 -o /dev/null -w '%{http_code}\n' \
    "https://query1.finance.yahoo.com/v8/finance/chart/$s?range=2d&interval=1d"
done
curl -s --max-time 20 -o /dev/null -w 'taifex %{http_code}\n' https://www.taifex.com.tw/cht/3/futContractsDate
```
預期：全數 `200`。任一非 200 → 在 `data-sources.md` 標記為不可用並保留 WebSearch 路徑，**不阻斷實作**。

### 步驟 4.7 放行 openapi.twse.com.tw
`.claude/hooks/block-domains.py`，在 `BLOCKED_DOMAINS` 後新增白名單並於 `is_blocked()` 開頭比對：

```python
# openapi.twse.com.tw serves JSON and returns 200 (verified 2026-09-15);
# only the www / rwd / mops paths 403 against WebFetch's user agent.
ALLOWED_HOSTS = ["openapi.twse.com.tw"]
```
```python
    if hostname in ALLOWED_HOSTS:
        return None
```

### 步驟 4.8 驗證封鎖邏輯
```bash
for u in https://openapi.twse.com.tw/v1/swagger.json \
         https://www.twse.com.tw/rwd/zh/fund/T86 \
         https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII \
         https://www.taifex.com.tw/cht/3/futContractsDate; do
  printf '%-60s ' "$u"
  echo "{\"tool_input\":{\"url\":\"$u\"}}" | python3 .claude/hooks/block-domains.py | grep -q deny && echo DENY || echo ALLOW
done
```
預期：第 2 個 `DENY`，其餘 `ALLOW`。

### 步驟 4.9 提交
```bash
git add -A && git commit -m "feat: 硬數據改由固定端點 WebFetch 取得（外資期貨/匯率/指數/報價）"
```

---

## Commit C5 — 內容層修正

### 步驟 5.1 修正盤前時序錯誤
`routines/01_premarket_tw.md:197`：
```
📈 *今日強勢族群 TOP 3*
```
→
```
📈 **開盤前相對強勢觀察**
（依前日收盤 + 隔夜美股傳導推導，非今日盤中表現）
```
第 198–200 行的三個項目格式同步改為 `**[族群]**`。

### 步驟 5.2 新增跨則去重規則
三個 routine 的「全域注意事項」各加一條：
> - **跨則去重**：同一事實（同一數據、同一事件）只在最相關的一則完整敘述；
>   其他則如需引用，限 15 字內指涉，不得重述數據。

（依據：9/15 盤前抽樣 11 個事實，有 8 個在 3 則全部出現。）

### 步驟 5.3 在 validate-report.py 加入去重偵測
於檔案頂端常數區新增：

```python
FACTS_FILE = "/tmp/claude_report_facts.json"
DEDUP_THRESHOLD = 5
```

新增函式：

```python
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
```

在 `main()` 中，**僅當 `hard` 為空時**呼叫（被硬門檻擋下的訊息不會送出，不應計入已見事實）：

```python
    hard, soft = validate_message(message)
    if not hard:
        soft += check_duplication(message)
```

### 步驟 5.4 在測試中加入去重案例
於 `test-validate-report.py` 追加一個獨立函式 `test_dedup()`：先 `os.remove(FACTS_FILE)`，
送入含 6 個數值的第 1 則（預期無警告），再送入重複其中 5 個數值的第 2 則（預期出現「跨則重複」），
最後送入只重複 1 個數值的第 3 則（預期無警告）。

### 步驟 5.5 執行完整測試
```bash
python3 .claude/hooks/test-validate-report.py
```
預期：全部 PASS（含 3 個去重案例）。

### 步驟 5.6 美股報價改表格（D2）
`routines/03_premarket_us.md` 第 2 則，將「MAG 7 盤前」與「半導體板塊深度」的條列改為表格骨架：

```
| 標的 | 盤前 | 動向 | 台股連動 |
|---|---|---|---|
| **AAPL** | $XXX (±X.XX%) | ... | 鴻海(2317)/大立光(3008) |
```
並在「美股 → 台股傳導鏈」同樣改為三欄表格（美股事件 / 傳導邏輯 / 台股標的）。
其餘敘述性段落維持條列。

### 步驟 5.7 提交
```bash
git add -A && git commit -m "feat: 跨則去重、盤前時序修正、美股報價表格化"
```

---

## Commit C6 — 同步 Codex 副本

### 步驟 6.1 複製 hooks
```bash
cp .claude/hooks/validate-report.py .claude/hooks/search-guard.py \
   .claude/hooks/log-execution.py .claude/hooks/block-domains.py \
   .claude/hooks/reset-counter.py .codex/hooks/
```

### 步驟 6.2 驗證 byte-identical
```bash
for f in validate-report search-guard log-execution block-domains reset-counter; do
  diff -q .claude/hooks/$f.py .codex/hooks/$f.py || echo "DIFF $f"
done
echo "sync check done"
```
預期：無 `DIFF` 輸出。

### 步驟 6.3 提交
```bash
git add -A && git commit -m "chore: 同步 .codex/hooks 與 .claude/hooks"
```

---

## 驗收（交由 /dev-verify）

1. `python3 .claude/hooks/test-validate-report.py` → 全數 PASS
2. 端點健康檢查（步驟 4.6）→ 全數 200，或已在 `data-sources.md` 標記不可用
3. `block-domains.py` 白名單驗證（步驟 4.8）→ 僅 `www.twse.com.tw` DENY
4. `search-guard.py` 第 9 次允許、第 10 次 DENY（步驟 3.3）
5. `.codex/hooks` 與 `.claude/hooks` byte-identical
6. `grep -rn "單星號" CLAUDE.md AGENTS.md .claude/ routines/` → 僅出現在「勿用單星號」的警語中
7. **端對端**：發一則測試訊息至 `C0B0B2K8857`，內含 `**粗體**`、`_斜體_`、一個表格、一個 `[文字](URL)` 連結，
   再用 `slack_read_channel` 回讀，確認儲存文字為 `*粗體*`（Slack bold）而非 `_粗體_`。
   這是唯一能證明格式修復的測試 — 本機無法驗證。
