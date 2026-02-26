# 🇻🇳 Dexter Vietnam — AI Phân Tích Chứng Khoán Việt Nam

> Trợ lý AI phân tích chứng khoán Việt Nam, tích hợp dữ liệu thực từ **vnstock**, phân tích kỹ thuật, cơ bản, dòng tiền và quản lý rủi ro.

---

## ✨ Tính năng chính

### 📊 Dữ liệu thị trường (`vnstock_connector`)
- Thông tin tổng quan công ty (ngành, vốn hoá, sàn niêm yết)
- Lịch sử giá OHLCV (mặc định 365 ngày)
- Báo cáo tài chính: Balance Sheet, Income Statement, Cash Flow
- Chỉ số tài chính: P/E, ROE, EPS, P/B...
- Dữ liệu khối ngoại mua/bán
- Chỉ số thị trường: VNINDEX, HNX, UPCOM

### 📈 Phân tích kỹ thuật (`technical_indicators`)
| Chỉ báo | Mô tả |
|---------|-------|
| RSI(14) | Quá mua/quá bán, phân kỳ |
| MACD(12,26,9) | Crossover, zero-line cross |
| Bollinger Bands(20) | %B, squeeze |
| SMA 20/50/200 | Golden/Death Cross |
| EMA 9/21/50 | Xu hướng ngắn/trung/dài |
| Stochastic(14) | %K/%D crossover |
| ATR(14) | Biến động, gợi ý stop-loss |

### 🎯 Tín hiệu giao dịch (`trading_signals`)
- RSI divergence (phân kỳ bullish/bearish)
- MACD crossover events theo lịch sử
- Golden Cross / Death Cross MA
- Hỗ trợ/kháng cự (Pivot Points, Swing H/L, Bollinger)
- Phân tích xu hướng 3 khung thời gian
- **Khuyến nghị MUA/BÁN** có trọng số + Stop-Loss/Take-Profit (ATR-based)

### 📋 Phân tích cơ bản (`financial_statements`, `financial_ratios`)
- Báo cáo tài chính chuẩn hoá (tiếng Anh, đơn vị tỷ đồng)
- Tăng trưởng YoY: doanh thu, lợi nhuận, EPS
- Đánh giá ngưỡng: P/E thấp/cao, ROE tốt/kém, D/E an toàn
- So sánh trend nhiều năm

### 💰 Dòng tiền (`money_flow`)
- OBV, Accumulation/Distribution, MFI (tự tính)
- Phân tích khối ngoại mua/bán ròng
- **Top 30 blue-chip** khối ngoại mua/bán nhiều nhất
- Phát hiện block trade (dấu hiệu giao dịch tổ chức)
- Giao dịch tự doanh CTCK và nội bộ HĐQT

### 📰 Tin tức & Tâm lý (`news_aggregator`, `sentiment_analysis`)
- Thu thập RSS từ **CafeF** và **VnExpress** theo thời gian thực
- Tìm kiếm tin theo mã cổ phiếu hoặc từ khoá
- Phân tích sentiment: Positive / Negative / Neutral (0.0 → 1.0)
- Hỗ trợ LLM sentiment (nếu có) hoặc keyword-based fallback
- Sentiment tổng quan thị trường

### ⚠️ Đánh giá rủi ro (`company_risk`)
- **Altman Z-Score** — dự báo xác suất phá sản
- Rủi ro thanh khoản: Current Ratio, Quick Ratio, Interest Coverage
- Biến động giá: Beta (so VNINDEX), Sharpe Ratio, VaR 95%, Max Drawdown
- **Rủi ro danh mục**: Correlation Matrix, HHI, Diversification Ratio
- Xếp hạng rủi ro tổng hợp: **A → F**

### 🔍 Sàng lọc cổ phiếu (`stock_screener`)
Scan ~80 mã blue-chip + mid-cap theo tiêu chí:

| Chiến lược | Tiêu chí mặc định |
|-----------|-------------------|
| **Value** | P/E ≤ 15, P/B ≤ 1.5, ROE ≥ 15%, D/E ≤ 1 |
| **Growth** | EPS tăng, Net margin tăng, ROE ≥ 12% |
| **Oversold** | RSI(14) < 30 |
| **Overbought** | RSI(14) > 70 |
| **Dividend** | Dividend yield ≥ 5% |
| **Industry** | Lọc theo 17 ngành (ngân hàng, BĐS, thép...) |
| **Custom** | Tự do kết hợp P/E, ROE, RSI, volume... |

### 🌐 Tổng quan thị trường (`market_overview`)
- Snapshot VNINDEX / HNX / UPCOM (close, change, H/L, volume)
- Top gainers / losers hàng ngày
- **Breadth**: A/D ratio, volume phân bổ tăng/giảm
- Hiệu suất 12 ngành và xếp hạng
- Chỉ số vĩ mô: lãi suất SBV, USD/VND (VCB), giá vàng SJC
- **Market Score 0-100**: tổng hợp index + breadth + sector

### 🧮 Công cụ tính toán (`calculators`)
- **Position Sizing** — khối lượng vào lệnh tối ưu theo % rủi ro + stop-loss
- **Tax & Phí** — thuế bán 0.1% + phí môi giới, lãi ròng thực tế
- **Breakeven** — giá hoà vốn sau nhiều lần mua
- **Margin** — call margin price, force sell, lãi vay theo ngày
- **DCA** — giá vốn bình quân, so sánh với lump sum
- **Lãi kép** — mô phỏng đầu tư dài hạn

---

## 🏗️ Kiến trúc

```
User Query
    │
    ▼
AgentOrchestrator
    │
    ├── ConversationMemory   ← Lưu ngữ cảnh hội thoại, entity resolution
    │
    ├── Planner (LLM)        ← Phân tích câu hỏi → tạo plan gọi tools
    │       └── Fallback: keyword-based rule nếu LLM lỗi
    │
    ├── Executor             ← Chạy tuần tự từng tool
    │       └── ToolRegistry ← Quản lý tất cả tools
    │
    └── Synthesizer (LLM)   ← Tổng hợp kết quả → trả lời tiếng Việt
```

### LLM hỗ trợ
| Provider | Model ví dụ |
|----------|------------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` |
| **Anthropic** | `claude-sonnet-4-20250514` |
| **Google** | `gemini-2.0-flash`, `gemini-1.5-pro` |

---

## 🚀 Cài đặt

```bash
# 1. Clone và tạo virtual environment
git clone <repo_url>
cd dexter_vietnam
python -m venv .venv

# 2. Kích hoạt venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt
```

## ⚙️ Cấu hình

```bash
cp .env.example .env
```

Chỉnh sửa `.env`:

```env
# Chọn LLM provider
LLM_PROVIDER=google          # openai | anthropic | google
LLM_MODEL=gemini-2.0-flash

# API Key tương ứng
OPENAI_API_KEY=sk-...
# hoặc
GOOGLE_API_KEY=AIza...
# hoặc
ANTHROPIC_API_KEY=sk-ant-...
```

## ▶️ Chạy ứng dụng

```bash
# Chat CLI
python main.py

# Hoặc dùng CLI với options
python cli.py --provider google --model gemini-2.0-flash
```

---

## 💬 Ví dụ câu hỏi

```
# Phân tích cổ phiếu
"Phân tích FPT"
"Kỹ thuật HPG hiện tại thế nào?"
"Báo cáo tài chính VNM 3 năm gần nhất"

# So sánh
"So sánh FPT và CMG về cơ bản và kỹ thuật"

# Thị trường
"Thị trường hôm nay?"
"Ngành nào đang dẫn dắt thị trường?"
"Khối ngoại đang mua gì?"

# Sàng lọc
"Lọc cổ phiếu giá trị P/E thấp ROE cao"
"Tìm cổ phiếu ngân hàng đang oversold"

# Tin tức & Dòng tiền
"Tin tức VCB hôm nay"
"Dòng tiền FPT đang vào hay ra?"

# Rủi ro
"Đánh giá rủi ro MBB"
"Rủi ro danh mục FPT 40%, VCB 30%, HPG 30%"
```

---

## 📦 Dependencies chính

| Package | Mục đích |
|---------|---------|
| `vnstock` | Dữ liệu chứng khoán Việt Nam |
| `ta` | Tính toán chỉ báo kỹ thuật |
| `pandas` / `numpy` | Xử lý dữ liệu |
| `requests` / `beautifulsoup4` | Crawl RSS tin tức, tỷ giá, vàng |
| `openai` / `anthropic` / `google-generativeai` | LLM API |

---

> ⚠️ **Disclaimer**: Đây là công cụ phân tích tham khảo, không phải khuyến nghị đầu tư. Hãy kết hợp với phân tích cá nhân và quản lý rủi ro trước khi ra quyết định.
