---
name: data-sources
description: 硬數據固定端點清單與取數規則。WebFetch 取得，不計搜尋次數。
---

# 硬數據來源（固定端點）

硬數據一律在第 0.5 步用 **WebFetch** 取得，**不計入搜尋次數**。
搜尋額度只用於敘事、事件與法人新聞。

## 1. 共通取數指令（必須寫進每個 WebFetch 的 prompt）

> 原樣回報數值，不得換算、不得四捨五入、不得推估。若頁面無該欄位，回答 `NOT_FOUND`。

## 2. 端點表

Yahoo chart API 路徑統一為
`https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?range=5d&interval=1d`
（美股盤前用 `range=2d`）。

| 用途 | URL | 取值欄位 | 狀態 |
|---|---|---|---|
| 加權指數 | `https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?range=5d&interval=1d` | `regularMarketPrice`、`chartPreviousClose` | ✅ 已實測（WebFetch） |
| USD/TWD | `https://query1.finance.yahoo.com/v8/finance/chart/TWD=X?range=2d&interval=1d` | `regularMarketPrice` | ✅ 已實測（WebFetch） |
| 外資台指期 | `https://www.taifex.com.tw/cht/3/futContractsDate` | 臺股期貨 → 外資及陸資 → 未平倉多空淨額口數 | ✅ 已實測（WebFetch） |
| 櫃買指數 | `.../chart/%5ETWOII` | 同加權 | ✅ 已實測（WebFetch，269.45 / 267.72） |
| 美股期貨 | `.../chart/ES=F`、`NQ=F`、`YM=F` | 同上 | ✅ `ES=F` 已實測（7668.5 / 7625.0）；`NQ=F`/`YM=F` 同類推定 |
| 費城半導體 | `.../chart/%5ESOX` | 同上 | ✅ 已實測（11131.281 / 11614.17） |
| VIX / 美元指數 | `.../chart/%5EVIX`、`.../chart/DX-Y.NYB` | 同上 | ✅ `DX-Y.NYB` 已實測（99.59 / 99.46）；`^VIX` 同類推定 |
| 美股個股 | `.../chart/{TICKER}`（NVDA/TSLA/TSM/QQQ/VOO…） | 同上 | ✅ `NVDA` 已實測（210.96 / 218.36）；其餘同類推定 |

⚠️ **限流註記（2026-09-15 健康檢查）**：以 `curl` 連續打 Yahoo chart API 會回 **HTTP 429
（Too Many Requests）**，query1/query2 皆然，換 browser user-agent 亦然；同時
`https://finance.yahoo.com/quote/%5ETWII/` 回 200。這是對命令列客戶端的 bot 限流，
不代表端點失效 —— 同一批符號改走 **WebFetch** 全數取得正確數值（`^TWII`、`TWD=X`、
`^TWOII`、`ES=F`、`^SOX`、`DX-Y.NYB`、`NVDA` 七項已逐一驗證，涵蓋台股指數／櫃買／匯率／
美股期貨／產業指數／美元指數／個股每一類）。
因此：**Yahoo 端點以 WebFetch 為唯一取數路徑，勿改用 Bash/curl**；
任一次 WebFetch 失敗或回 `NOT_FOUND`，直接走第 4 節回退規則，不重試、不中斷。

備援來源（Yahoo 全數失敗時）：
- 加權指數 / 成交值（億元）：`https://www.cnyes.com/twstock/`（WebFetch 可用）
- 其餘：WebSearch 讀結果摘要

## 3. 漲跌幅推導規則

`漲跌幅 = (regularMarketPrice - chartPreviousClose) / chartPreviousClose`

兩者皆為交易所官方收盤價，相除屬算術，**不屬於「自行推算」禁令**
（該禁令針對用 ADR 反推匯率）。

## 4. 回退規則（D4）

任一端點失敗或回 `NOT_FOUND` → 走原本的 WebSearch 路徑，
並在第 3 則末行「資料來源」欄註記，例：

> `_本日外資期貨改由媒體彙整；USD/TWD 改由搜尋摘要取得_`

**端點失敗不得中斷 routine，也不得列為硬門檻。**

## 5. 禁止事項

不得對 `www.twse.com.tw`、`goodinfo.tw`、`histock.tw`、`sinotrade.com.tw`、
`wantgoo.com`、`investing.com` 執行 WebFetch。

`openapi.twse.com.tw` 為例外，允許（回 200，供 JSON 取數）。
