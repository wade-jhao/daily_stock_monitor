---
name: ground-truth-us
description: 美股 routine 的 Ground Truth 驗證框架。期貨和核心個股盤前報價為最高優先。
---

# Ground Truth 驗證框架（美股版）

## GT 登記表

第 0.5 步的硬數據為 ground truth（固定端點 WebFetch，⟹ 見 .claude/skills/data-sources.md；
禁止 WebFetch investing.com）。撰寫每則訊息前，必須建立內部「GT 登記表」並逐項比對：

- GT_FUTURES_DOW：道瓊期貨 = [Yahoo `chart/YM=F`]
- GT_FUTURES_SPX：標普期貨 = [Yahoo `chart/ES=F`]
- GT_FUTURES_NQ：那指期貨 = [Yahoo `chart/NQ=F`]
- GT_SOX：費城半導體 = [Yahoo `chart/%5ESOX`]
- GT_NVDA：NVDA 盤前價 = [Yahoo `chart/NVDA`]
- GT_TSLA：TSLA 盤前價 = [Yahoo `chart/TSLA`]

漲跌幅 = (regularMarketPrice − chartPreviousClose) / chartPreviousClose，屬算術，非「自行推算」。
任一端點失敗或回 NOT_FOUND → 走 WebSearch 摘要回退並於第 3 則末行註記；**端點失敗不列硬門檻**。

## 🔴 硬門檻（任一不過 → 該則訊息禁止發送，改發品質警告）

1. 期貨方向與 GT 正負相反 → BLOCK
2. NVDA/TSLA 價格與 GT 差距 > 3% → BLOCK
3. 台股代碼不在代碼表中且無新聞來源確認 → BLOCK
4. 關鍵數據位出現模糊數字（~、約、X）→ BLOCK
5. 「即將發布」事件未經時效校驗即引用 → BLOCK

## 🟡 軟門檻（記錄但繼續發送）

6. 搜尋次數達上限
7. 部分區段省略
8. 期權/ETF 數據未取得

## 🔴 硬門檻觸發時的替代訊息

```
⚠️ **品質檢查未通過**
本則報告因以下問題暫停發送：• [具體問題] • [GT 數據 vs 報告數據]
_關鍵數據請直接查閱 finance.yahoo.com_
```

發送替代訊息後，嘗試修正問題並重新撰寫。修正後仍不過則保留替代訊息，繼續下一則。
