# Daily Stock Monitor - Agent Instructions

本專案為自動化股市分析報告系統，透過 Slack 發送到 #daily_wade_monitor。

## 全域規則（所有 routine 必須遵守）

1. **封鎖網域**：twse.com.tw、goodinfo.tw、histock.tw、sinotrade.com.tw、wantgoo.com 永遠回傳 403，禁止 WebFetch
2. **股票代碼**：群聯=8299（不是 8046），8046=南電。所有代碼必須查表確認
3. **數據品質**：禁止模糊數字（~、約、X）、禁止自算匯率、禁止編造籌碼
4. **格式**：Slack mrkdwn 單星號粗體 `*文字*`，禁止雙星號、HTML、# 標題
5. **效率**：取不到的數據直接省略，不留空殼佔版面
6. **定位**：資訊整理，非投資建議。禁止「建議買進/賣出」

## 資料來源優先順序

可用：cnyes.com、ctee.com.tw、money.udn.com、investing.com、moneydj.com、tw.stock.yahoo.com、cmoney.tw
禁用：twse.com.tw、goodinfo.tw、histock.tw、sinotrade.com.tw、wantgoo.com

## Skills 參考

- `stock-analysis`：量價四型態判讀、真強/誘多判別、期現貨組合判讀
- `supply-chain-map`：美股→台股完整供應鏈傳導對照
- `data-quality-check`：發送前品質檢查流程

## Hooks 自動執行

- SessionStart：重置搜尋計數器
- PreToolUse (Slack send)：品質門檻檢查（代碼、格式、模糊數字）
- PostToolUse (WebSearch)：搜尋次數追蹤與警告
- Stop：記錄執行 log
