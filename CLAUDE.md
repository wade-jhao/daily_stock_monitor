# Daily Stock Monitor - CLAUDE.md

## Project Overview

This project powers automated stock market analysis reports delivered via Slack to #daily_wade_monitor (C0B0B2K8857).
The system consists of 4 Claude Code routines (remote triggers) that run on schedule.

## Routines

| Routine | Schedule (UTC) | Taiwan Time | Frequency |
|---------|---------------|-------------|-----------|
| 台股盤前摘要 | `30 0 * * 1-5` | ~08:30 Mon-Fri | Daily |
| 台股盤後深度 | `30 9 * * 1-5` | ~17:30 Mon-Fri | Daily |
| 美股盤前實戰 | `0 11 * * 1,3` | ~19:00 Mon+Wed | Bi-weekly |
| AI Weekly Review | `0 1 * * 1` | ~09:00 Mon | Weekly |

Output: 3 Slack messages per stock report, 1 message for AI weekly review.
Channel: C0B0B2K8857 (#daily_wade_monitor)
Slack Connector UUID: 8afb2353-9fc1-446d-8c36-da276557abdf

## Known Blocked URLs (HTTP 403 - DO NOT attempt WebFetch)

These URLs consistently return 403 errors. Do NOT waste search quota on them:

- `twse.com.tw/zh/trading/foreign/*` (TWSE T86 法人日報)
- `twse.com.tw/rwd/zh/fund/*` (TWSE 基金頁面)
- `mops.twse.com.tw/*` (公開資訊觀測站)
- `goodinfo.tw/*` (Goodinfo 台股)
- `histock.tw/*` (HiStock)
- `sinotrade.com.tw/*` (新光證券)
- `wantgoo.com/*` (玩股網)
- `fubon-ebrokerdj.fbs.com.tw/*` (富邦 e01)

## Recommended Alternative Data Sources

### 三大法人買賣超 TOP 10
1. Google 搜尋「三大法人買賣超 [日期]」→ 取媒體報導版本
2. 鉅亨網 anue.bz 搜尋「三大法人」→ 新聞稿中通常有前 5-10 名
3. 經濟日報 money.udn.com 搜尋「法人買超」
4. Yahoo 股市新聞 tw.stock.yahoo.com
5. CMoney 新聞 www.cmoney.tw
6. MoneyDJ 新聞 www.moneydj.com

### 大盤收盤數據
1. 鉅亨網 anue.bz（首選，穩定可取得）
2. 經濟日報 money.udn.com
3. 工商時報 ctee.com.tw
4. Yahoo 股市 tw.stock.yahoo.com

### 美股/國際數據
1. Investing.com（首選，期貨、指數、匯率、原物料）
2. CNBC、Bloomberg（個股報價）
3. Yahoo Finance（Pre-Market 報價）
4. MarketWatch

### 台幣匯率
1. Google 搜尋「台幣匯率」或「USD TWD」
2. Investing.com
3. 鉅亨網外匯頁面

### 除權息/法說會
1. Google 搜尋「[日期] 除權息」或「[日期] 法說會」
2. 鉅亨網行事曆
3. MoneyDJ 行事曆

## Stock Code Reference Table (預設追蹤清單)

### AI 伺服器
鴻海(2317), 廣達(2382), 緯創(3231), 緯穎(6669), 技嘉(2376), 英業達(2356)

### 半導體上游
台積電(2330), 聯電(2303), 世界先進(5347), 力積電(6770), 家登(3680), 辛耘(3583)

### IC 設計
聯發科(2454), 聯詠(3034), 瑞昱(2379), 譜瑞-KY(4966), 創意(3443), 世芯-KY(3661)

### 封測/測試
日月光投控(3711), 京元電(2449), 力成(6239), 頎邦(6147),
穎崴(6515), 欣銓(3264), 精測(6510), 旺矽(6223)

### 記憶體
南亞科(2408), 華邦電(2344), 旺宏(2337), 群聯(8299), 威剛(3260), 十銓(4967), 晶豪科(3006)
**注意**: 群聯代碼是 8299，不是 8046。8046 是南電。

### 光通訊/CPO/矽光子
聯亞(3081), 聯鈞(3450), 華星光(4979), 上詮(3323), 波若威(3163), 眾達-KY(4977),
光聖(6442), 台表科(6278)

### PCB/ABF 載板
欣興(3037), 南電(8046), 景碩(3189), 台光電(2383), 台燿(6274), 聯茂(6213), 金像電(2368),
臻鼎-KY(4958), 華通(2313)

### 被動元件
國巨(2327), 華新科(2492), 奇力新(2456)

### 散熱
雙鴻(3324), 奇鋐(3017), 建準(2421), 力致(3444)

### 電源/連接器
台達電(2308), 光寶科(2301), 健策(3653), 嘉澤(3533), 貿聯-KY(3665)

### 網通設備
智邦(2345), 智易(3596), 中磊(5388), 啟碁(6285)

### 重電/電網
華城(1519), 中興電(1513), 士電(1503), 亞力(1514)

### FOPLP 面板級封裝
群創(3481), 友達(2409), 元太(8069)

### 低軌衛星
昇達科(3491), 華通(2313), 兆赫(2485)

### 化合物半導體/第三類半導體
穩懋(3105), 漢磊(3707), 富采(3714)

### 半導體高價指標
信驊(5274)

### 機器人/自動化
上銀(2049), 所羅門(2359), 盟立(2464)

### NB/PC + AI PC + 電競 + 遊戲機
華碩(2357), 宏碁(2353), 微星(2377), 技嘉(2376), 仁寶(2324), 和碩(4938),
原相(3227), 致伸(4915), 群光(2385)

### 蘋概股
大立光(3008), 玉晶光(3406), 鴻準(2354)

### 特斯拉供應鏈
和大(1536), 貿聯-KY(3665), 台達電(2308), 上銀(2049)

## Banned Practices (嚴禁行為)

1. **嚴禁自行推算匯率** - 不得用 ADR 價格與台股價格反推 USD/TWD 匯率
2. **嚴禁使用模糊數字** - 不寫「31.X」「YY.X 元」「~平盤」，要嘛精確要嘛省略
3. **嚴禁編造籌碼數據** - 券商分點、借券、融資融券無確認來源就不寫
4. **嚴禁 WebFetch 已知封鎖網站** - 參見上方 Known Blocked URLs
5. **嚴禁超出 Web Search 次數上限** - 盤前 7 次、盤後 8 次、美股 9 次
6. **嚴禁股票代碼錯誤** - 必須參照本文件代碼表，特別注意群聯(8299)≠南電(8046)

## Content Quality Guidelines

### 法人 TOP 10 處理原則
- 優先透過 Google 搜尋新聞報導取得（不直接 WebFetch TWSE）
- 能取得多少就列多少，最低標準 3 名
- 每檔必須包含：個股名稱、代碼、張數、所屬族群
- 無法取得時標註「資料來源受限，以下為媒體報導確認的法人動向」

### 無法取得的區段處理
- 券商分點異動：除非從新聞報導中明確取得，否則整個區段改為 1 行標註「_今日券商分點資料未能取得_」
- 借券賣出異動：同上處理
- 外資期貨部位：從新聞報導取得方向性資訊即可，不需精確口數

### 新興雷達品質要求
- 每項必須有具體催化劑（新聞事件、法人動向、量價變化）
- 至少 1 項應具備前瞻性（尚未被主流媒體廣泛報導的觀察）
- 科技題材優先，非科技「有料才寫」

### 執行時間控制
- 資料蒐集階段：最多 12 分鐘
- 訊息撰寫階段：最多 8 分鐘
- 總執行時間上限：20 分鐘
- 若接近 15 分鐘仍在搜尋，立即進入撰寫

## Slack mrkdwn Format Reminder

- 粗體：`*文字*`（單星號）
- 斜體：`_文字_`
- 程式碼：`` `文字` ``
- 列表：`•` 開頭
- 連結：`<URL|顯示文字>`
- 禁止：HTML 標籤、雙星號 `**`、`#` 標題語法
