# 🗺️ CODING ROADMAP - Dexter Vietnam AI Trading Assistant

**Lộ trình phát triển 18 modules trong 8 tuần**

---

## 📋 Tổng quan dự án

### Mục tiêu
Xây dựng AI Trading Assistant cho thị trường chứng khoán Việt Nam với khả năng:
- Phân tích cơ bản & kỹ thuật
- Theo dõi dòng tiền & tin tức
- Đánh giá rủi ro & sàng lọc cổ phiếu
- AI Agent tương tác bằng ngôn ngữ tự nhiên

### Tech Stack
- **Language**: Python 3.11+
- **Data Source**: vnstock3 (primary), TCBS/SSI (backup)
- **LLM**: OpenAI/Anthropic/Google Gemini
- **Analysis**: pandas, ta (technical analysis)
- **CLI**: rich, click

---

## 🏗️ Cấu trúc dự án

```
dexter_vietnam/
├── agent/              # AI Agent core
│   └── orchestrator.py
├── tools/              # Công cụ phân tích
│   ├── base.py
│   ├── registry.py
│   └── vietnam/
│       ├── data/           # Module 1: Dữ liệu
│       ├── fundamental/    # Module 2: Phân tích cơ bản
│       ├── technical/      # Module 3: Phân tích kỹ thuật
│       ├── money_flow/     # Module 4: Dòng tiền
│       ├── news/           # Module 5: Tin tức
│       ├── risk/           # Module 6: Rủi ro
│       ├── screening/      # Module 7: Sàng lọc
│       ├── market/         # Module 10: Thị trường
│       ├── alerts/         # Module 11: Cảnh báo
│       ├── reporting/      # Module 12: Báo cáo
│       ├── calculators/    # Module 13: Tính toán
│       ├── education/      # Module 14: Giáo dục
│       ├── social/         # Module 15: Cộng đồng
│       ├── ai/             # Module 17: AI nâng cao
│       └── premium/        # Module 18: Premium
├── model/              # LLM wrapper
├── utils/              # Utilities
├── tests/              # Unit tests
├── main.py
├── cli.py
└── requirements.txt
```

---

## 📦 Module 1: Hạ tầng Dữ liệu (P0)

**File**: `tools/vietnam/data/vnstock_connector.py`

### Việc cần làm
1. Tạo class `VnstockTool` kế thừa `BaseTool`
2. Implement các methods lấy dữ liệu từ vnstock
3. Error handling & retry logic
4. Unit tests

### Chức năng & vnstock Endpoints

| Chức năng | Method | vnstock API |
|-----------|--------|-------------|
| Thông tin công ty | `get_stock_overview(symbol)` | `stock.company.profile()` |
| Lịch sử giá | `get_stock_price(symbol, start, end)` | `stock.quote.history()` |
| Báo cáo tài chính | `get_financial_report(symbol, type, period)` | `stock.finance.balance_sheet()` / `income_statement()` / `cash_flow()` |
| Chỉ số tài chính | `get_financial_ratio(symbol, period)` | `stock.finance.ratio()` |
| Giao dịch khối ngoại | `get_foreign_trading(symbol)` | `stock.trading.price_depth()` |
| Danh sách mã CP | `get_all_symbols(exchange)` | `stock.listing.all_symbols()` |
| Chỉ số thị trường | `get_market_index(index_code)` | `stock.quote.history()` với VNINDEX/HNX/UPCOM |

**Tài liệu**: https://vnstock.site/

---

## 📊 Module 2: Phân tích Cơ bản (P0)

**File**: `tools/vietnam/fundamental/`

### 2.1 Financial Statements Parser
**File**: `financial_statements.py`

**Việc cần làm**:
- Parse Balance Sheet (Tài sản, Nợ, Vốn chủ)
- Parse Income Statement (Doanh thu, Chi phí, Lợi nhuận)
- Parse Cash Flow (Hoạt động, Đầu tư, Tài chính)

### 2.2 Financial Ratios Calculator
**File**: `ratios.py`

**Chức năng cần implement**:
- P/E, P/B, P/S ratios
- ROE, ROA, ROIC
- Debt/Equity, Current Ratio, Quick Ratio
- EPS, BVPS
- Gross Margin, Net Margin

### 2.3 DCF Valuation
**File**: `dcf_valuation.py`

**Việc cần làm**:
- Tính WACC (Weighted Average Cost of Capital)
- Dự báo Free Cash Flow
- Tính Terminal Value
- Tính giá trị nội tại (Intrinsic Value)

**Formula**: `DCF = Σ(FCF_t / (1+WACC)^t) + Terminal Value / (1+WACC)^n`

---

## 📈 Module 3: Phân tích Kỹ thuật (P0)

**File**: `tools/vietnam/technical/`

### 3.1 Technical Indicators
**File**: `indicators.py`

**Sử dụng thư viện `ta`**

**Chức năng cần implement**:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- EMA/SMA (Exponential/Simple Moving Average)
- Stochastic Oscillator
- ATR (Average True Range)

### 3.2 Trading Signals
**File**: `signals.py`

**Việc cần làm**:
- Detect RSI overbought/oversold (>70/<30)
- Detect MACD crossover
- Detect Golden Cross / Death Cross
- Support/Resistance levels
- Trend detection

---

## 💰 Module 4: Dòng Tiền (P1)

**File**: `tools/vietnam/money_flow/`

### Chức năng

| Chức năng | Method | Mô tả |
|-----------|--------|-------|
| Khối ngoại | `get_foreign_trading(symbol, date)` | Mua/bán ròng khối ngoại |
| Top mua ròng | `get_top_foreign_buying(top_n)` | Top N CP khối ngoại mua |
| Top bán ròng | `get_top_foreign_selling(top_n)` | Top N CP khối ngoại bán |
| Tự doanh | `get_proprietary_trading(symbol)` | Giao dịch tự doanh |
| Nội bộ | `get_insider_trading(symbol)` | Giao dịch nội bộ |

**Data source**: vnstock `stock.trading.price_depth()`

---

## 📰 Module 5: Tin tức & Sự kiện (P1)

**File**: `tools/vietnam/news/`

### 5.1 News Aggregator
**File**: `aggregator.py`

**Nguồn tin**:
- CafeF: https://cafef.vn
- VnExpress: https://vnexpress.net/kinh-doanh
- Vietstock: https://vietstock.vn
- ĐTCK: https://baodautu.vn

**Chức năng**:
- `get_latest_news(symbol, limit)` - Tin mới nhất
- `search_news(keyword, from_date, to_date)` - Tìm kiếm

**Tech**: BeautifulSoup4 / Playwright

### 5.2 Sentiment Analysis
**File**: `sentiment.py`

**Việc cần làm**:
- Dùng LLM phân tích tâm lý bài báo
- Return: `{sentiment: positive/negative/neutral, score: 0-1, reasoning: string}`

---

## ⚠️ Module 6: Quản lý Rủi ro (P2)

**File**: `tools/vietnam/risk/company_risk.py`

### Chức năng

| Chức năng | Method | Mô tả |
|-----------|--------|-------|
| Altman Z-Score | `calculate_altman_z_score(financial_data)` | Dự đoán phá sản (>2.99: an toàn, <1.81: nguy hiểm) |
| Liquidity Risk | `assess_liquidity_risk(current_ratio, quick_ratio)` | Rủi ro thanh khoản |
| Portfolio Risk | `calculate_portfolio_risk(holdings)` | Rủi ro danh mục |

---

## 🔍 Module 7: Stock Screening (P2)

**File**: `tools/vietnam/screening/screener.py`

### Chức năng

**Việc cần làm**:
- `screen_value_stocks(criteria)` - Lọc CP giá trị (P/E<15, P/B<1.5, ROE>15%, D/E<1)
- `screen_growth_stocks(criteria)` - Lọc CP tăng trưởng
- `screen_oversold(rsi_threshold)` - Lọc CP oversold (RSI<30)
- `screen_by_industry(industry, criteria)` - Lọc theo ngành

---

## 🌐 Module 10: Market Overview (P1)

**File**: `tools/vietnam/market/overview.py`

### Chức năng

| Chức năng | Method | Output |
|-----------|--------|--------|
| Tổng quan TT | `get_market_status()` | VNINDEX, HNX, UPCOM status + top gainers/losers |
| Hiệu suất ngành | `get_sector_performance()` | Banking, Steel, Real Estate, Oil & Gas performance |
| Chỉ số vĩ mô | `get_macro_indicators()` | Lãi suất, lạm phát, GDP |

---

## 🔔 Module 11: Alerts (P3)

**File**: `tools/vietnam/alerts/manager.py`

### Chức năng
- `create_price_alert(symbol, target_price, condition)` - Cảnh báo giá
- `create_news_alert(symbol, keywords)` - Cảnh báo tin tức
- `check_alerts(current_data)` - Kiểm tra alerts

**Storage**: SQLite hoặc JSON file

---

## 📄 Module 12: Reporting (P3)

**File**: `tools/vietnam/reporting/generator.py`

### Chức năng
- `generate_daily_report(portfolio_id)` - Báo cáo ngày
- `generate_weekly_report(portfolio_id)` - Báo cáo tuần
- `export_to_pdf(report_data)` - Export PDF

---

## 🧮 Module 13: Calculators (P3)

**File**: `tools/vietnam/calculators/basic.py`

### Chức năng
- `calculate_compound_interest(principal, rate, time, monthly)` - Lãi kép
- `calculate_position_sizing(capital, risk, entry, stop_loss)` - Khối lượng vào lệnh
- `calculate_tax(profit, holding_period)` - Thuế

---

## 📚 Module 14: Education (P3)

**File**: `tools/vietnam/education/knowledge.py`

### Chức năng
- `get_term_definition(term)` - Giải thích thuật ngữ
- `get_tutorial(topic)` - Hướng dẫn
- `get_case_study(symbol)` - Case study

**Storage**: Vector DB (ChromaDB/Pinecone) hoặc JSON

---

## 👥 Module 15: Social (P3)

**File**: `tools/vietnam/social/community.py`

### Chức năng
- `get_top_portfolios()` - Top danh mục hiệu quả
- `get_leaderboard()` - Bảng xếp hạng
- `share_portfolio(portfolio_id)` - Chia sẻ danh mục

---

## 🤖 Module 17: Advanced AI (P4)

**File**: `tools/vietnam/ai/prediction.py`

### Chức năng
- `predict_next_day(symbol)` - Dự báo xu hướng (LSTM/Transformer)
- `detect_anomaly(financial_data)` - Phát hiện bất thường

**Models**: TensorFlow/PyTorch

---

## 💎 Module 18: Premium Features (P4)

**File**: `tools/vietnam/premium/level2.py`

### Chức năng
- `get_market_depth(symbol)` - Dữ liệu 10 bước giá
- `get_intraday_data(symbol, interval)` - Dữ liệu phút

**Data source**: Premium APIs (SSI Pro, VPS, etc.)

---

## 🤖 Agent Core System

**File**: `agent/orchestrator.py`

### Việc cần làm

1. **Planner**: Phân tích query → Lập kế hoạch tools cần gọi
2. **Executor**: Thực thi tools song song
3. **Synthesizer**: Tổng hợp kết quả → Trả lời user
4. **Memory**: Lưu conversation history

**Flow**: `User Query → Plan → Execute Tools → Synthesize → Response`

---

## 🗓️ Lộ trình 8 tuần

### Tuần 1-2: Core Infrastructure (P0)
- [ ] Module 1: vnstock connector
- [ ] Module 2: Fundamental analysis
- [ ] Base tool system & registry
- [ ] Unit tests

### Tuần 3: Technical Analysis (P0)
- [ ] Module 3: Indicators & signals
- [ ] Integration tests

### Tuần 4: Money Flow & News (P1)
- [ ] Module 4: Foreign/Proprietary trading
- [ ] Module 5: News aggregator & sentiment

### Tuần 5: Risk & Screening (P1-P2)
- [ ] Module 6: Risk management
- [ ] Module 7: Stock screening
- [ ] Module 10: Market overview

### Tuần 6: Agent Core
- [ ] Agent orchestrator
- [ ] Planner, Executor, Synthesizer
- [ ] CLI interface (rich/click)

### Tuần 7: Interaction Tools (P3)
- [ ] Module 11-15: Alerts, Reporting, Calculators, Education, Social

### Tuần 8: Advanced & Polish (P4)
- [ ] Module 17-18: AI prediction, Premium features
- [ ] Performance optimization
- [ ] Documentation & deployment

---

## 📊 Bảng tổng kết

| Module | Tên | Priority | Tuần | Status |
|--------|-----|----------|------|--------|
| 1 | Data Infrastructure | P0 | 1-2 | 🟡 In Progress |
| 2 | Fundamental Analysis | P0 | 1-2 | ⚪ Not Started |
| 3 | Technical Analysis | P0 | 3 | ⚪ Not Started |
| 4 | Money Flow | P1 | 4 | ⚪ Not Started |
| 5 | News & Events | P1 | 4 | ⚪ Not Started |
| 6 | Risk Management | P2 | 5 | ⚪ Not Started |
| 7 | Stock Screening | P2 | 5 | ⚪ Not Started |
| 10 | Market Overview | P1 | 5 | ⚪ Not Started |
| 11 | Alerts | P3 | 7 | ⚪ Not Started |
| 12 | Reporting | P3 | 7 | ⚪ Not Started |
| 13 | Calculators | P3 | 7 | ⚪ Not Started |
| 14 | Education | P3 | 7 | ⚪ Not Started |
| 15 | Social | P3 | 7 | ⚪ Not Started |
| 17 | Advanced AI | P4 | 8 | ⚪ Not Started |
| 18 | Premium Features | P4 | 8 | ⚪ Not Started |

---

## 🎯 Mục tiêu

### MVP (Tuần 1-5)
- ✅ Lấy dữ liệu từ vnstock
- ✅ Phân tích cơ bản & kỹ thuật
- ✅ Theo dõi dòng tiền & tin tức
- ✅ AI Agent trả lời: "Phân tích VNM", "Khối ngoại mua gì?"

### Full Product (Tuần 6-8)
- ✅ CLI interface đẹp
- ✅ Alert system
- ✅ Báo cáo tự động
- ✅ AI prediction

---

## 📚 Tài liệu tham khảo

- **vnstock**: https://vnstock.site/
- **Technical Analysis**: https://technical-analysis-library-in-python.readthedocs.io/
- **LangChain**: https://python.langchain.com/

---

**🚀 Bắt đầu code ngay!**
