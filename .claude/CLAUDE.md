# Daily Stock Monitor - Agent Instructions

本專案為自動化股市分析報告系統，透過 Slack 發送到 #daily_wade_monitor。

## 全域規則（所有 routine 必須遵守）

1. **封鎖網域**：twse.com.tw、goodinfo.tw、histock.tw、sinotrade.com.tw、wantgoo.com 永遠回傳 403，禁止 WebFetch
2. **股票代碼**：群聯=8299（不是 8046），8046=南電。所有代碼必須查表確認
3. **數據品質**：禁止模糊數字（~、約、X）、禁止自算匯率、禁止編造籌碼
4. **格式**：標準 Markdown。粗體 `**文字**`（單星號 `*文字*` 會變斜體）、斜體 `_文字_`、表格可用。禁止 HTML、`#` 標題
5. **效率**：取不到的數據直接省略，不留空殼佔版面
6. **定位**：資訊整理，非投資建議。禁止「建議買進/賣出」

## 資料來源優先順序

硬數據（WebFetch 固定端點，不計搜尋次數）：⟹ 讀取 `.claude/skills/data-sources.md`
  指數/匯率/期貨/個股報價走 Yahoo chart API；外資台指期走 taifex.com.tw。**這些端點只能用 WebFetch，不可用 Bash/curl（會被限流擋下）**
可用（WebFetch）：cnyes.com、ctee.com.tw、money.udn.com、moneydj.com、tw.stock.yahoo.com、cmoney.tw、openapi.twse.com.tw
回退取數（勿 WebFetch，常 403）：investing.com — 僅在上述端點失效時，才改用 WebSearch 讀結果摘要（讀摘要≠自算匯率，合法）
禁用：www.twse.com.tw、goodinfo.tw、histock.tw、sinotrade.com.tw、wantgoo.com

## Skills 參考（.claude/skills/）

Routine prompt 透過 `⟹ 讀取 .claude/skills/xxx.md` 引用 skill，不內嵌內容。

| Skill | 用途 | 引用者 |
|-------|------|--------|
| `stock-analysis` | 量價四型態、真強/誘多、期現貨組合判讀 | 盤後 |
| `supply-chain-map` | 美股→台股傳導對照表 | 美股 |
| `stock-code-table` | 完整股票代碼表（群聯=8299） | 全部 |
| `data-sources` | 硬數據固定端點表（Yahoo/TAIFEX）、取數措辭、回退規則 | 全部 |
| `ground-truth-tw` | 台股 GT 登記表 + 硬/軟門檻 | 盤前、盤後 |
| `ground-truth-us` | 美股 GT 登記表（期貨/個股） | 美股 |
| `quality-gate-tw` | 台股發送前品質門檻（代碼/格式/合規/長度/搜尋；數值門檻見 ground-truth-tw） | 盤前、盤後 |
| `quality-gate-us` | 美股發送前品質門檻（數值門檻見 ground-truth-us） | 美股 |

## Hooks 自動執行

- SessionStart：重置搜尋計數器
- PreToolUse (Slack send)：品質門檻檢查 — 🔴 硬門檻擋發送（代碼/模糊數字/模板）、🟡 軟門檻警告放行（格式/空殼/超長）
- PreToolUse (WebSearch)：搜尋次數追蹤與警告
- PreToolUse (WebFetch)：封鎖網域攔截
- Stop：記錄執行 log

## 跨 Routine 記憶層（Step 0.3）

每個 routine 開頭透過 slack_read_channel 讀取前次報告作為 context：
- 盤前 ← 前日盤後 + 美股（limit=12）
- 盤後 ← 今日盤前（limit=6）
- 美股 ← 今日盤後（limit=6）

讀取失敗不阻斷，透過標題前綴識別報告（「台股摘要」「台股盤後深度」「美股盤前實戰」）。
