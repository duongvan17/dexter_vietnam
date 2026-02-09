"""
Module 14: Education - Kiến thức đầu tư chứng khoán

Theo CODING_ROADMAP.md - Module 14:
- get_term_definition(term): Giải thích thuật ngữ chứng khoán
- get_tutorial(topic): Hướng dẫn / bài học theo chủ đề
- get_case_study(symbol): Case study phân tích CP cụ thể
- list_terms(category): Liệt kê thuật ngữ theo nhóm
- quiz(topic): Câu hỏi kiểm tra kiến thức

Storage: JSON (built-in knowledge base)
"""
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
import logging
import random

logger = logging.getLogger(__name__)


# =====================================================================
# KNOWLEDGE BASE - Thuật ngữ chứng khoán Việt Nam
# =====================================================================

TERM_DATABASE: Dict[str, Dict[str, Any]] = {
    # --- Thuật ngữ cơ bản ---
    "p/e": {
        "term": "P/E (Price to Earnings)",
        "category": "fundamental",
        "vi": "Hệ số giá trên thu nhập",
        "definition": (
            "P/E = Giá cổ phiếu / EPS (Thu nhập trên mỗi cổ phiếu). "
            "Cho biết nhà đầu tư sẵn sàng trả bao nhiêu đồng cho 1 đồng lợi nhuận."
        ),
        "formula": "P/E = Market Price per Share / Earnings per Share (EPS)",
        "interpretation": [
            "P/E < 10: Có thể đang rẻ hoặc DN gặp khó khăn",
            "P/E 10-15: Mức hợp lý cho các ngành truyền thống",
            "P/E 15-25: Mức cao, cần xem tăng trưởng có tương xứng",
            "P/E > 25: Đắt, kỳ vọng tăng trưởng cao hoặc đang bong bóng",
        ],
        "vietnam_context": (
            "Trên TTCK Việt Nam, P/E trung bình VN-Index thường dao động 12-18. "
            "Ngành ngân hàng P/E ~8-12, bất động sản ~10-20, công nghệ ~20-30."
        ),
        "example": "VNM có P/E = 18, nghĩa là NĐT trả 18,000đ cho mỗi 1,000đ lợi nhuận.",
        "related": ["p/b", "eps", "peg"],
    },
    "p/b": {
        "term": "P/B (Price to Book)",
        "category": "fundamental",
        "vi": "Hệ số giá trên giá trị sổ sách",
        "definition": (
            "P/B = Giá cổ phiếu / Giá trị sổ sách mỗi cổ phiếu (BVPS). "
            "So sánh giá thị trường với giá trị tài sản ròng của doanh nghiệp."
        ),
        "formula": "P/B = Market Price / Book Value per Share",
        "interpretation": [
            "P/B < 1: Cổ phiếu giao dịch dưới giá trị sổ sách (có thể là cơ hội hoặc DN yếu)",
            "P/B = 1-2: Mức hợp lý",
            "P/B > 3: Đắt, thường ở DN có lợi thế cạnh tranh mạnh",
        ],
        "vietnam_context": "Ngành ngân hàng Việt Nam thường có P/B 1.0-2.5. BĐS 0.5-2.0.",
        "example": "ACB có P/B = 1.5, thị trường định giá 1.5 lần giá trị sổ sách.",
        "related": ["p/e", "bvps", "roe"],
    },
    "eps": {
        "term": "EPS (Earnings per Share)",
        "category": "fundamental",
        "vi": "Thu nhập trên mỗi cổ phiếu",
        "definition": (
            "EPS = (Lợi nhuận sau thuế - Cổ tức ưu đãi) / Số CP đang lưu hành. "
            "Đo lường khả năng sinh lời trên mỗi cổ phiếu."
        ),
        "formula": "EPS = (Net Income - Preferred Dividends) / Shares Outstanding",
        "interpretation": [
            "EPS tăng liên tục: DN tăng trưởng tốt",
            "EPS giảm: Cần xem nguyên nhân (chu kỳ hay cấu trúc)",
            "So sánh EPS với cùng ngành để đánh giá",
        ],
        "vietnam_context": "EPS trung bình VN30 khoảng 3,000-5,000 VND/CP.",
        "example": "FPT có EPS = 5,200 VND, tức mỗi CP mang lại 5,200đ lợi nhuận.",
        "related": ["p/e", "net_income", "diluted_eps"],
    },
    "roe": {
        "term": "ROE (Return on Equity)",
        "category": "fundamental",
        "vi": "Tỷ suất sinh lời trên vốn chủ sở hữu",
        "definition": (
            "ROE = Lợi nhuận sau thuế / Vốn chủ sở hữu bình quân. "
            "Đo lường hiệu quả sử dụng vốn cổ đông."
        ),
        "formula": "ROE = Net Income / Average Shareholders' Equity × 100%",
        "interpretation": [
            "ROE > 15%: Hiệu quả sử dụng vốn tốt",
            "ROE > 20%: Xuất sắc",
            "ROE < 10%: Cần xem xét kỹ",
            "ROE cao + D/E thấp: Doanh nghiệp chất lượng",
        ],
        "vietnam_context": (
            "ROE trung bình thị trường VN ~12-15%. Ngân hàng tốt >18%, "
            "sản xuất >15% là đáng chú ý."
        ),
        "example": "VCB có ROE = 22%, rất tốt so với trung bình ngành ngân hàng.",
        "related": ["roa", "roic", "dupont"],
    },
    "roa": {
        "term": "ROA (Return on Assets)",
        "category": "fundamental",
        "vi": "Tỷ suất sinh lời trên tổng tài sản",
        "definition": (
            "ROA = Lợi nhuận sau thuế / Tổng tài sản bình quân. "
            "Đo lường hiệu quả sử dụng tài sản."
        ),
        "formula": "ROA = Net Income / Average Total Assets × 100%",
        "interpretation": [
            "ROA > 5%: Tốt (phụ thuộc ngành)",
            "Ngân hàng: ROA > 1.5% là tốt (vì đòn bẩy cao)",
            "Sản xuất: ROA > 8% là tốt",
        ],
        "vietnam_context": "ROA ngân hàng VN tốt >1.5%. Phi tài chính >5% là khá.",
        "example": "TCB có ROA = 2.8%, cao nhất nhóm ngân hàng tư nhân.",
        "related": ["roe", "asset_turnover"],
    },
    "rsi": {
        "term": "RSI (Relative Strength Index)",
        "category": "technical",
        "vi": "Chỉ số sức mạnh tương đối",
        "definition": (
            "RSI đo lường tốc độ và biên độ thay đổi giá, dao động 0-100. "
            "Xác định trạng thái quá mua (overbought) hoặc quá bán (oversold)."
        ),
        "formula": "RSI = 100 - (100 / (1 + RS)), RS = Avg Gain / Avg Loss (14 phiên)",
        "interpretation": [
            "RSI > 70: Quá mua (overbought) → Có thể điều chỉnh",
            "RSI < 30: Quá bán (oversold) → Có thể phục hồi",
            "RSI 40-60: Vùng trung tính",
            "Phân kỳ RSI (divergence) là tín hiệu mạnh",
        ],
        "vietnam_context": (
            "Trên TTCK VN, RSI < 30 thường xuất hiện ở đáy ngắn hạn. "
            "Kết hợp RSI + MACD + khối lượng cho tín hiệu đáng tin hơn."
        ),
        "example": "VNM RSI = 25 → oversold, có thể cân nhắc mua nếu nền tảng cơ bản tốt.",
        "related": ["macd", "stochastic", "bollinger"],
    },
    "macd": {
        "term": "MACD (Moving Average Convergence Divergence)",
        "category": "technical",
        "vi": "Đường trung bình hội tụ phân kỳ",
        "definition": (
            "MACD = EMA(12) - EMA(26). Signal Line = EMA(9) của MACD. "
            "Xác định xu hướng và tín hiệu mua/bán dựa trên giao cắt."
        ),
        "formula": "MACD Line = EMA(12) - EMA(26), Signal = EMA(9) of MACD",
        "interpretation": [
            "MACD cắt lên Signal: Tín hiệu MUA",
            "MACD cắt xuống Signal: Tín hiệu BÁN",
            "MACD > 0: Xu hướng tăng",
            "MACD < 0: Xu hướng giảm",
            "Histogram tăng/giảm: Đà tăng/giảm đang mạnh lên",
        ],
        "vietnam_context": (
            "MACD crossover kết hợp volume tăng trên TTCK VN "
            "thường cho tín hiệu đáng tin cậy hơn."
        ),
        "example": "FPT MACD cắt lên signal line + volume tăng → tín hiệu mua kỹ thuật.",
        "related": ["rsi", "ema", "sma", "golden_cross"],
    },
    "bollinger": {
        "term": "Bollinger Bands",
        "category": "technical",
        "vi": "Dải Bollinger",
        "definition": (
            "Dải giá gồm 3 đường: SMA(20) ở giữa, ±2 độ lệch chuẩn. "
            "Đo lường biến động và xác định vùng quá mua/quá bán."
        ),
        "formula": "Upper = SMA(20) + 2σ, Lower = SMA(20) - 2σ",
        "interpretation": [
            "Giá chạm dải trên: Có thể quá mua",
            "Giá chạm dải dưới: Có thể quá bán",
            "Dải thu hẹp (squeeze): Chuẩn bị biến động mạnh",
            "Dải mở rộng: Đang trong xu hướng mạnh",
        ],
        "vietnam_context": "Bollinger squeeze trên VN-Index thường báo hiệu breakout lớn.",
        "example": "HPG chạm Bollinger band dưới + RSI < 30 → tín hiệu oversold mạnh.",
        "related": ["rsi", "sma", "volatility"],
    },
    "golden_cross": {
        "term": "Golden Cross / Death Cross",
        "category": "technical",
        "vi": "Giao cắt vàng / Giao cắt tử thần",
        "definition": (
            "Golden Cross: SMA(50) cắt lên SMA(200) → Xu hướng tăng dài hạn. "
            "Death Cross: SMA(50) cắt xuống SMA(200) → Xu hướng giảm dài hạn."
        ),
        "formula": "Golden Cross: SMA(50) crosses above SMA(200)",
        "interpretation": [
            "Golden Cross: Tín hiệu mua dài hạn, xác suất tăng cao",
            "Death Cross: Tín hiệu bán dài hạn, cẩn trọng",
            "Cần xác nhận bằng volume và chỉ báo khác",
        ],
        "vietnam_context": (
            "VN-Index Golden Cross xuất hiện ~2-3 lần/năm. "
            "Death Cross năm 2022 báo trước đợt giảm mạnh."
        ),
        "example": "VN-Index SMA(50) cắt lên SMA(200) tháng 1/2023 → rally mạnh.",
        "related": ["sma", "ema", "trend"],
    },
    "support_resistance": {
        "term": "Support & Resistance",
        "category": "technical",
        "vi": "Hỗ trợ & Kháng cự",
        "definition": (
            "Support: Mức giá mà lực mua đủ mạnh để ngăn giá giảm thêm. "
            "Resistance: Mức giá mà lực bán đủ mạnh để ngăn giá tăng thêm."
        ),
        "formula": "Xác định bằng: Đỉnh/đáy trước, Fibonacci, Pivot Points, Volume Profile",
        "interpretation": [
            "Breakout qua resistance + volume → tín hiệu mua mạnh",
            "Breakdown dưới support + volume → tín hiệu bán",
            "Resistance cũ trở thành support mới sau breakout",
            "Nhiều lần test cùng mức → mức đó càng mạnh",
        ],
        "vietnam_context": (
            "VN-Index có các mức hỗ trợ/kháng cự tâm lý: 1,000 / 1,100 / 1,200 / 1,300 điểm."
        ),
        "example": "HPG thường có hỗ trợ mạnh tại vùng giá 22-23, kháng cự tại 28-30.",
        "related": ["fibonacci", "pivot_point", "breakout"],
    },
    "d/e": {
        "term": "D/E (Debt to Equity)",
        "category": "fundamental",
        "vi": "Hệ số nợ trên vốn chủ sở hữu",
        "definition": (
            "D/E = Tổng nợ / Vốn chủ sở hữu. "
            "Đo lường mức độ sử dụng đòn bẩy tài chính."
        ),
        "formula": "D/E = Total Debt / Shareholders' Equity",
        "interpretation": [
            "D/E < 0.5: An toàn, ít đòn bẩy",
            "D/E 0.5-1.0: Mức bình thường",
            "D/E 1.0-2.0: Đòn bẩy cao, cần xem khả năng trả nợ",
            "D/E > 2.0: Rủi ro cao (trừ ngành ngân hàng, BĐS)",
        ],
        "vietnam_context": (
            "Ngân hàng VN thường D/E rất cao (>8) do đặc thù ngành. "
            "Doanh nghiệp sản xuất nên D/E < 1.5."
        ),
        "example": "VIC có D/E = 2.3, cao do đầu tư BĐS lớn, cần xem dòng tiền.",
        "related": ["current_ratio", "interest_coverage", "leverage"],
    },
    "dcf": {
        "term": "DCF (Discounted Cash Flow)",
        "category": "fundamental",
        "vi": "Dòng tiền chiết khấu",
        "definition": (
            "DCF định giá doanh nghiệp bằng cách chiết khấu dòng tiền tự do tương lai "
            "về giá trị hiện tại, sử dụng tỷ lệ chiết khấu (WACC)."
        ),
        "formula": "DCF = Σ(FCF_t / (1+WACC)^t) + Terminal Value / (1+WACC)^n",
        "interpretation": [
            "DCF > Giá hiện tại: Cổ phiếu đang undervalued",
            "DCF < Giá hiện tại: Cổ phiếu đang overvalued",
            "Margin of Safety = (DCF - Price) / DCF × 100%",
            "DCF nhạy cảm với giả định WACC và growth rate",
        ],
        "vietnam_context": (
            "DCF trên TTCK VN thường dùng WACC 10-14%, growth rate 5-15%. "
            "Terminal growth thường dùng 3-5% (GDP growth)."
        ),
        "example": "FPT DCF = 130,000 VND/CP, giá thị trường 100,000 → undervalued ~30%.",
        "related": ["wacc", "fcf", "terminal_value", "intrinsic_value"],
    },
    "fibonacci": {
        "term": "Fibonacci Retracement",
        "category": "technical",
        "vi": "Fibonacci thoái lui",
        "definition": (
            "Công cụ xác định các mức hỗ trợ/kháng cự dựa trên dãy Fibonacci. "
            "Các mức quan trọng: 23.6%, 38.2%, 50%, 61.8%, 78.6%."
        ),
        "formula": "Retracement Level = High - (High - Low) × Fibonacci %",
        "interpretation": [
            "38.2%: Mức pullback nhẹ trong xu hướng mạnh",
            "50.0%: Mức thoái lui trung bình",
            "61.8%: Mức vàng (golden ratio) - quan trọng nhất",
            "78.6%: Mức sâu, xu hướng có thể đảo chiều",
        ],
        "vietnam_context": (
            "Fibonacci 61.8% trên VN-Index thường là mức hỗ trợ/kháng cự mạnh. "
            "Kết hợp với volume profile cho kết quả tốt hơn."
        ),
        "example": "VN-Index pullback từ 1,300 về 1,200 (Fib 38.2%) rồi bật tăng lại.",
        "related": ["support_resistance", "elliott_wave"],
    },
    "margin_trading": {
        "term": "Margin Trading",
        "category": "trading",
        "vi": "Giao dịch ký quỹ",
        "definition": (
            "Vay tiền từ công ty chứng khoán để mua cổ phiếu. "
            "Tỷ lệ ký quỹ ban đầu thường 50% (vay 1:1), duy trì 30-35%."
        ),
        "formula": "Buying Power = Equity / Initial Margin Ratio",
        "interpretation": [
            "Lợi: Tăng sức mua, khuếch đại lợi nhuận",
            "Hại: Khuếch đại thua lỗ, lãi vay 12-15%/năm",
            "Call margin: Khi equity/value < maintenance ratio",
            "Force sell: Khi equity < force sell threshold",
        ],
        "vietnam_context": (
            "Tỷ lệ margin TTCK VN: ban đầu ~50-70%, duy trì ~30-40%. "
            "Lãi suất margin: 12-15%/năm. UBCKNN quy định danh sách CP được margin."
        ),
        "example": "100M vốn, margin 50% → mua 200M CP. Nếu CP giảm 25%, mất 50M = 50% vốn.",
        "related": ["call_margin", "leverage", "risk_management"],
    },
    "t_plus": {
        "term": "T+0, T+1, T+2 (Settlement Cycle)",
        "category": "trading",
        "vi": "Chu kỳ thanh toán",
        "definition": (
            "Thời gian từ khi đặt lệnh đến khi thanh toán hoàn tất. "
            "T+0: Trong ngày, T+1: Ngày tiếp theo, T+2: 2 ngày sau."
        ),
        "formula": "T = Trade date, +N = số ngày thanh toán",
        "interpretation": [
            "HOSE: T+2 (từ 2022, trước đó T+3)",
            "HNX: T+2",
            "Bán cổ phiếu T+0, tiền về T+2",
            "T+0 chỉ áp dụng cho chứng chỉ quỹ ETF",
        ],
        "vietnam_context": (
            "Từ 29/08/2022 TTCK VN áp dụng T+2. "
            "Nhiều CTCK cho phép mua bán T+0 bằng tiền margin."
        ),
        "example": "Mua CP thứ 2, thanh toán hoàn tất thứ 4 (T+2).",
        "related": ["margin_trading", "order_types"],
    },
    "order_types": {
        "term": "Order Types (Loại lệnh)",
        "category": "trading",
        "vi": "Các loại lệnh giao dịch",
        "definition": "Các hình thức đặt lệnh mua/bán cổ phiếu trên sàn chứng khoán.",
        "formula": "N/A",
        "interpretation": [
            "LO (Limit Order): Lệnh giới hạn, chỉ khớp tại giá đặt hoặc tốt hơn",
            "ATO: Lệnh mở cửa, khớp giá mở cửa (HOSE 9:00-9:15)",
            "ATC: Lệnh đóng cửa, khớp giá đóng cửa (HOSE 14:30-14:45)",
            "MP (Market Price): Lệnh thị trường, khớp giá tốt nhất",
            "MOK (Match or Kill): Khớp hết hoặc huỷ",
            "MAK (Match and Kill): Khớp được bao nhiêu khớp bấy nhiêu, huỷ phần còn lại",
        ],
        "vietnam_context": (
            "HOSE: LO, ATO, ATC, MP. "
            "HNX: LO, ATO, ATC, MOK, MAK, MTL. "
            "Biên độ dao động: HOSE ±7%, HNX ±10%, UPCOM ±15%."
        ),
        "example": "Đặt LO mua VNM 78.5 → chỉ khớp khi giá ≤ 78.5.",
        "related": ["t_plus", "lot_size", "price_step"],
    },
    "lot_size": {
        "term": "Lot Size (Đơn vị giao dịch)",
        "category": "trading",
        "vi": "Lô giao dịch",
        "definition": (
            "Số lượng cổ phiếu tối thiểu cho 1 lệnh giao dịch. "
            "HOSE: 100 CP/lô, HNX: 100 CP/lô."
        ),
        "formula": "Giá trị lệnh = Lô × 100 × Giá CP",
        "interpretation": [
            "Lô chẵn: Bội số của 100 CP",
            "Lô lẻ: Dưới 100 CP, giao dịch riêng trên hệ thống lô lẻ",
            "Giao dịch lô lẻ thường có giá thấp hơn 1-3%",
        ],
        "vietnam_context": (
            "Từ 04/01/2021 HOSE chuyển sang lô 100 CP (trước đó 10 CP). "
            "Giá trị tối thiểu 1 lô: 100 × giá CP. Ví dụ: VNM ~8 triệu."
        ),
        "example": "Mua tối thiểu 1 lô = 100 CP. Nếu VNM giá 80, cần 8 triệu VND.",
        "related": ["order_types", "t_plus"],
    },
    "candlestick": {
        "term": "Candlestick (Nến Nhật)",
        "category": "technical",
        "vi": "Biểu đồ nến Nhật Bản",
        "definition": (
            "Biểu đồ thể hiện 4 mức giá: Open, High, Low, Close trong 1 phiên. "
            "Nến xanh: Close > Open (tăng). Nến đỏ: Close < Open (giảm)."
        ),
        "formula": "Body = |Close - Open|, Upper Shadow = High - max(O,C), Lower Shadow = min(O,C) - Low",
        "interpretation": [
            "Nến Doji: O ≈ C, thân rất nhỏ → thị trường do dự",
            "Nến Hammer: Thân nhỏ + bóng dưới dài → đáy tiềm năng",
            "Nến Engulfing: Nến sau bao trùm nến trước → đảo chiều",
            "Nến Morning Star: 3 nến → đáy đảo chiều tăng",
            "Nến Shooting Star: Thân nhỏ + bóng trên dài → đỉnh tiềm năng",
        ],
        "vietnam_context": "Mô hình nến kết hợp volume trên TTCK VN rất hữu ích cho swing trading.",
        "example": "Hammer xuất hiện tại vùng hỗ trợ + volume tăng → cơ hội mua.",
        "related": ["support_resistance", "volume", "trend"],
    },
    "volume": {
        "term": "Volume (Khối lượng giao dịch)",
        "category": "technical",
        "vi": "Khối lượng giao dịch",
        "definition": (
            "Tổng số cổ phiếu được giao dịch trong 1 phiên. "
            "Volume xác nhận xu hướng giá."
        ),
        "formula": "Volume = Tổng số CP được mua bán trong phiên",
        "interpretation": [
            "Giá tăng + Volume tăng: Xu hướng tăng mạnh, xác nhận",
            "Giá tăng + Volume giảm: Xu hướng yếu, có thể đảo chiều",
            "Giá giảm + Volume tăng: Áp lực bán mạnh",
            "Volume đột biến: Có thể có sự kiện quan trọng",
        ],
        "vietnam_context": (
            "Volume trung bình HOSE: ~600-800 triệu CP/phiên. "
            "Volume > 1 tỷ CP: Phiên giao dịch sôi động."
        ),
        "example": "HPG volume tăng 3x trung bình + giá breakout → tín hiệu mạnh.",
        "related": ["obv", "vwap", "liquidity"],
    },
    "dividend": {
        "term": "Dividend (Cổ tức)",
        "category": "fundamental",
        "vi": "Cổ tức",
        "definition": (
            "Phần lợi nhuận công ty chia cho cổ đông. "
            "Có thể bằng tiền mặt hoặc cổ phiếu."
        ),
        "formula": "Dividend Yield = Annual Dividend per Share / Stock Price × 100%",
        "interpretation": [
            "Dividend yield > 5%: Khá hấp dẫn",
            "Cổ tức tiền mặt ổn định: DN tài chính lành mạnh",
            "Cổ tức cổ phiếu: Pha loãng nhưng không mất tiền",
            "Ngày GDKHQ: Mua trước ngày này mới được nhận cổ tức",
        ],
        "vietnam_context": (
            "Nhiều DN VN trả cổ tức bằng CP (pha loãng 10-30%/năm). "
            "DN trả cổ tức tiền mặt cao: ngân hàng, tiện ích, thực phẩm."
        ),
        "example": "VNM trả cổ tức ~4,000đ/CP/năm, yield ~5% → phù hợp đầu tư dài hạn.",
        "related": ["eps", "payout_ratio", "ex_date"],
    },
    "wacc": {
        "term": "WACC (Weighted Average Cost of Capital)",
        "category": "fundamental",
        "vi": "Chi phí vốn bình quân gia quyền",
        "definition": (
            "WACC tính trung bình có trọng số chi phí các nguồn vốn "
            "(nợ vay + vốn chủ sở hữu) dùng để chiết khấu dòng tiền."
        ),
        "formula": "WACC = E/(E+D) × Re + D/(E+D) × Rd × (1-T)",
        "interpretation": [
            "WACC thấp → DN có lợi thế chi phí vốn",
            "Dùng làm tỷ suất chiết khấu trong DCF",
            "ROIC > WACC: DN tạo giá trị cho cổ đông",
        ],
        "vietnam_context": (
            "WACC trung bình DN Việt Nam: 10-14%. "
            "Chi phí vốn chủ sở hữu thường 12-18% (risk premium cao)."
        ),
        "example": "WACC VNM = 11%, ROIC = 25% → DN tạo giá trị rất tốt.",
        "related": ["dcf", "capm", "cost_of_equity"],
    },
    "beta": {
        "term": "Beta (β)",
        "category": "fundamental",
        "vi": "Hệ số Beta",
        "definition": (
            "Beta đo lường mức độ biến động của cổ phiếu so với thị trường. "
            "β = 1: biến động như thị trường, β > 1: biến động hơn."
        ),
        "formula": "β = Cov(Ri, Rm) / Var(Rm)",
        "interpretation": [
            "β = 1.0: CP biến động bằng thị trường",
            "β > 1.0: CP biến động hơn (rủi ro cao, lợi nhuận tiềm năng cao)",
            "β < 1.0: CP ít biến động hơn (phòng thủ)",
            "β < 0: CP ngược chiều thị trường (hiếm)",
        ],
        "vietnam_context": (
            "CP ngân hàng VN thường β = 1.0-1.3. "
            "CP thép, BĐS: β = 1.5-2.0. CP tiện ích: β = 0.5-0.8."
        ),
        "example": "HPG β = 1.8, khi VN-Index tăng 1%, HPG có thể tăng ~1.8%.",
        "related": ["alpha", "sharpe_ratio", "volatility"],
    },
    "free_float": {
        "term": "Free Float",
        "category": "trading",
        "vi": "Tỷ lệ tự do chuyển nhượng",
        "definition": (
            "Phần trăm cổ phiếu lưu hành có thể giao dịch tự do trên thị trường. "
            "Loại trừ CP cổ đông lớn, CP hạn chế chuyển nhượng."
        ),
        "formula": "Free Float = (CP lưu hành - CP hạn chế) / CP lưu hành × 100%",
        "interpretation": [
            "Free float cao (>50%): Thanh khoản tốt, dễ giao dịch",
            "Free float thấp (<20%): Thanh khoản kém, dễ bị đẩy giá",
            "Tăng free float: MSCI/ETF quốc tế dễ mua vào hơn",
        ],
        "vietnam_context": (
            "Free float trung bình VN30: ~30-50%. Nhiều DN nhà nước free float <30%. "
            "MSCI đánh giá VN dựa trên free float để nâng hạng."
        ),
        "example": "VCB free float ~23%, thấp → room ngoại hạn chế.",
        "related": ["market_cap", "liquidity", "foreign_ownership"],
    },
}


# =====================================================================
# TUTORIALS DATABASE - Hướng dẫn đầu tư
# =====================================================================

TUTORIAL_DATABASE: Dict[str, Dict[str, Any]] = {
    "beginner": {
        "title": "🎯 Hướng dẫn cho Người mới bắt đầu",
        "category": "beginner",
        "sections": [
            {
                "title": "1. Mở tài khoản chứng khoán",
                "content": (
                    "• Chọn CTCK uy tín: SSI, VNDirect, MBS, TCBS, VPS\n"
                    "• Mở TK online (10-15 phút) hoặc tại quầy\n"
                    "• Cần: CMND/CCCD, số điện thoại, email, tài khoản ngân hàng\n"
                    "• TK giao dịch thường (margin sau 6 tháng)\n"
                    "• Nạp tiền vào TK qua chuyển khoản ngân hàng"
                ),
            },
            {
                "title": "2. Kiến thức cơ bản",
                "content": (
                    "• 3 sàn: HOSE, HNX, UPCOM\n"
                    "• Lô giao dịch: 100 CP (HOSE & HNX)\n"
                    "• Phiên giao dịch: 9:00-11:30, 13:00-14:45\n"
                    "• Biên độ: HOSE ±7%, HNX ±10%, UPCOM ±15%\n"
                    "• Thanh toán T+2\n"
                    "• Thuế bán: 0.1%, phí môi giới: 0.15-0.5%"
                ),
            },
            {
                "title": "3. Nguyên tắc đầu tư an toàn",
                "content": (
                    "• Chỉ đầu tư tiền nhàn rỗi (không vay để đầu tư)\n"
                    "• Phân bổ vốn: không >20% vào 1 CP\n"
                    "• Luôn đặt stop loss (cắt lỗ 7-10%)\n"
                    "• Học trước khi mua, đừng theo tin đồn\n"
                    "• Bắt đầu với số vốn nhỏ để lấy kinh nghiệm\n"
                    "• Kiên nhẫn, không giao dịch quá nhiều"
                ),
            },
        ],
    },
    "fundamental_analysis": {
        "title": "📊 Phân tích Cơ bản (Fundamental Analysis)",
        "category": "analysis",
        "sections": [
            {
                "title": "1. Phân tích Top-Down",
                "content": (
                    "• Kinh tế vĩ mô → Ngành → Doanh nghiệp\n"
                    "• Vĩ mô: GDP, lãi suất, lạm phát, tỷ giá\n"
                    "• Ngành: Chu kỳ ngành, cung cầu, cạnh tranh\n"
                    "• DN: Doanh thu, lợi nhuận, ban lãnh đạo"
                ),
            },
            {
                "title": "2. Chỉ số quan trọng",
                "content": (
                    "• Định giá: P/E, P/B, EV/EBITDA\n"
                    "• Sinh lời: ROE, ROA, ROIC, margins\n"
                    "• Đòn bẩy: D/E, Interest Coverage\n"
                    "• Tăng trưởng: Revenue growth, EPS growth\n"
                    "• Chất lượng: FCF/Net Income, Altman Z-Score"
                ),
            },
            {
                "title": "3. Đọc BCTC",
                "content": (
                    "• Bảng CĐKT: Tài sản, Nợ, Vốn chủ\n"
                    "• KQKD: Doanh thu → Chi phí → Lợi nhuận\n"
                    "• LCTT: CF hoạt động > 0, CF đầu tư (capex), CF tài chính\n"
                    "• Thuyết minh BCTC: Chi tiết quan trọng thường nằm ở đây\n"
                    "• So sánh quý/quý, năm/năm, so với ngành"
                ),
            },
            {
                "title": "4. Định giá",
                "content": (
                    "• DCF: Chiết khấu dòng tiền tự do (chính xác nhất)\n"
                    "• P/E relative: So sánh P/E với ngành/lịch sử\n"
                    "• P/B + ROE: Graham formula (BVPS × √(22.5 × EPS × BVPS))\n"
                    "• Margin of Safety: Chỉ mua khi giá < giá trị 20-30%"
                ),
            },
        ],
    },
    "technical_analysis": {
        "title": "📈 Phân tích Kỹ thuật (Technical Analysis)",
        "category": "analysis",
        "sections": [
            {
                "title": "1. Nền tảng",
                "content": (
                    "• Giá phản ánh tất cả\n"
                    "• Giá chuyển động theo xu hướng (trend)\n"
                    "• Lịch sử lặp lại (mô hình giá)\n"
                    "• 3 loại trend: Uptrend, Downtrend, Sideways"
                ),
            },
            {
                "title": "2. Chỉ báo kỹ thuật chính",
                "content": (
                    "• Xu hướng: SMA, EMA, MACD\n"
                    "• Đà: RSI, Stochastic, CCI\n"
                    "• Biến động: Bollinger Bands, ATR\n"
                    "• Khối lượng: OBV, Volume Profile\n"
                    "• Kết hợp ≥2 chỉ báo để xác nhận"
                ),
            },
            {
                "title": "3. Mô hình giá quan trọng",
                "content": (
                    "• Đảo chiều: Head & Shoulders, Double Top/Bottom\n"
                    "• Tiếp diễn: Flag, Pennant, Triangle\n"
                    "• Breakout + Volume = Tín hiệu mạnh\n"
                    "• Fibonacci retracement: 38.2%, 50%, 61.8%"
                ),
            },
            {
                "title": "4. Quản lý giao dịch",
                "content": (
                    "• Entry: Xác nhận xu hướng + chỉ báo + volume\n"
                    "• Stop loss: Đặt dưới support hoặc -7%\n"
                    "• Take profit: R:R ≥ 2:1 hoặc trailing stop\n"
                    "• Position sizing: Không quá 2% vốn/lệnh rủi ro"
                ),
            },
        ],
    },
    "risk_management": {
        "title": "🛡️ Quản lý Rủi ro (Risk Management)",
        "category": "strategy",
        "sections": [
            {
                "title": "1. Quy tắc vàng",
                "content": (
                    "• Rule 2%: Không risking quá 2% tổng vốn trên 1 lệnh\n"
                    "• Rule 6%: Tổng rủi ro mở không quá 6% vốn\n"
                    "• Rule 1:2+: Risk:Reward tối thiểu 1:2\n"
                    "• Luôn đặt stop loss trước khi vào lệnh"
                ),
            },
            {
                "title": "2. Position Sizing",
                "content": (
                    "• Số CP = (Vốn × %Rủi ro) / (Entry - Stop Loss)\n"
                    "• Ví dụ: 100M × 2% / (50 - 47) = 666 CP → 600 CP (6 lô)\n"
                    "• Pyramiding: Thêm vị thế khi đúng xu hướng\n"
                    "• Scaling out: Bán từng phần khi đạt target"
                ),
            },
            {
                "title": "3. Đa dạng hoá",
                "content": (
                    "• 5-10 CP trên ≥3 ngành khác nhau\n"
                    "• Không >20% vốn vào 1 CP\n"
                    "• Mix: Cổ phiếu + Trái phiếu + Tiền mặt\n"
                    "• Rebalance danh mục hàng quý"
                ),
            },
            {
                "title": "4. Tâm lý giao dịch",
                "content": (
                    "• Kỷ luật: Tuân thủ kế hoạch, không FOMO\n"
                    "• Kiên nhẫn: Đợi setup đẹp, không ép giao dịch\n"
                    "• Chấp nhận thua: Cắt lỗ nhanh, để lãi chạy\n"
                    "• Ghi nhật ký giao dịch (trading journal)"
                ),
            },
        ],
    },
    "value_investing": {
        "title": "💎 Đầu tư Giá trị (Value Investing)",
        "category": "strategy",
        "sections": [
            {
                "title": "1. Triết lý",
                "content": (
                    "• Benjamin Graham & Warren Buffett\n"
                    "• Mua doanh nghiệp tốt với giá hợp lý\n"
                    "• Margin of Safety: Giá < Giá trị nội tại 20-30%\n"
                    "• Đầu tư dài hạn (≥3-5 năm)"
                ),
            },
            {
                "title": "2. Tiêu chí lọc CP giá trị",
                "content": (
                    "• P/E < 15 (hoặc < trung bình ngành)\n"
                    "• P/B < 1.5\n"
                    "• ROE > 15% liên tục 3-5 năm\n"
                    "• D/E < 1.0\n"
                    "• EPS tăng trưởng 5 năm\n"
                    "• Cổ tức ổn định"
                ),
            },
            {
                "title": "3. Phân tích chất lượng (Moat)",
                "content": (
                    "• Thương hiệu mạnh: VNM, SAB, MWG\n"
                    "• Chi phí chuyển đổi cao: Ngân hàng, Phần mềm\n"
                    "• Hiệu ứng mạng lưới: FPT Telecom, Viettel\n"
                    "• Lợi thế chi phí: HPG (thép), GAS\n"
                    "• Ban lãnh đạo có năng lực & liêm chính"
                ),
            },
        ],
    },
    "swing_trading": {
        "title": "🔄 Swing Trading",
        "category": "strategy",
        "sections": [
            {
                "title": "1. Khái niệm",
                "content": (
                    "• Giữ vị thế 3-20 phiên\n"
                    "• Tận dụng dao động ngắn hạn trong xu hướng\n"
                    "• Kết hợp kỹ thuật + cơ bản\n"
                    "• Phù hợp người đi làm (không cần canh ngày)"
                ),
            },
            {
                "title": "2. Setup Swing",
                "content": (
                    "• Pullback trong uptrend: Mua khi giá về SMA(20)\n"
                    "• Breakout khỏi consolidation + volume\n"
                    "• RSI oversold (< 30) trong uptrend dài hạn\n"
                    "• Hammer tại support + volume tăng"
                ),
            },
            {
                "title": "3. Quản lý lệnh",
                "content": (
                    "• Entry: Xác nhận bằng nến đảo chiều\n"
                    "• Stop loss: Dưới swing low hoặc -5-7%\n"
                    "• Target: R:R ≥ 2:1 hoặc vùng kháng cự\n"
                    "• Trailing stop: Di chuyển SL theo trend"
                ),
            },
        ],
    },
    "dca": {
        "title": "📅 DCA - Dollar Cost Averaging",
        "category": "strategy",
        "sections": [
            {
                "title": "1. Khái niệm",
                "content": (
                    "• Mua cổ phiếu/ETF đều đặn hàng tháng\n"
                    "• Cùng số tiền, bất kể giá thị trường\n"
                    "• Giảm rủi ro timing, trung bình giá mua\n"
                    "• Phù hợp đầu tư dài hạn (≥3 năm)"
                ),
            },
            {
                "title": "2. Ưu điểm",
                "content": (
                    "• Không cần canh thời điểm mua\n"
                    "• Kỷ luật đầu tư tự động\n"
                    "• Mua nhiều hơn khi giá rẻ, ít hơn khi giá cao\n"
                    "• Giảm tác động tâm lý FOMO/panic"
                ),
            },
            {
                "title": "3. Thực hành tại VN",
                "content": (
                    "• Chọn CP blue-chip: VNM, FPT, VCB, MWG\n"
                    "• Hoặc ETF: FUEVFVND, FUESSV50\n"
                    "• Mua mỗi tháng cùng ngày (ví dụ ngày 15)\n"
                    "• Số tiền: 3-10 triệu VND/tháng\n"
                    "• Sử dụng tính năng 'lệnh tự động' của CTCK"
                ),
            },
        ],
    },
    "reading_financial_statements": {
        "title": "📝 Cách đọc Báo cáo Tài chính",
        "category": "analysis",
        "sections": [
            {
                "title": "1. Bảng cân đối kế toán (Balance Sheet)",
                "content": (
                    "• Tài sản = Nợ + Vốn chủ sở hữu\n"
                    "• Nợ ngắn hạn vs Nợ dài hạn\n"
                    "• Hàng tồn kho tăng nhanh → cẩn trọng\n"
                    "• Phải thu tăng nhanh hơn doanh thu → red flag\n"
                    "• Tiền mặt nhiều → doanh nghiệp an toàn"
                ),
            },
            {
                "title": "2. Kết quả kinh doanh (Income Statement)",
                "content": (
                    "• Doanh thu thuần tăng trưởng ổn định?\n"
                    "• Lợi nhuận gộp margin ổn định/tăng?\n"
                    "• Chi phí quản lý có kiểm soát?\n"
                    "• Lợi nhuận thuần / Doanh thu (Net Margin)\n"
                    "• Lợi nhuận bất thường (one-off items)"
                ),
            },
            {
                "title": "3. Lưu chuyển tiền tệ (Cash Flow Statement)",
                "content": (
                    "• CF hoạt động > 0: DN tạo tiền từ hoạt động chính\n"
                    "• CF đầu tư < 0: Đang mở rộng (tốt nếu hiệu quả)\n"
                    "• CF tài chính: Vay nợ, trả cổ tức, mua lại CP\n"
                    "• FCF = CF hoạt động - CapEx → tiền thực sự còn lại\n"
                    "• Red flag: Lãi trên giấy nhưng CF hoạt động âm"
                ),
            },
        ],
    },
}


# =====================================================================
# QUIZ DATABASE - Câu hỏi kiểm tra kiến thức
# =====================================================================

QUIZ_DATABASE: Dict[str, List[Dict[str, Any]]] = {
    "fundamental": [
        {
            "question": "P/E = 20 nghĩa là gì?",
            "options": [
                "A. Giá CP gấp 20 lần lợi nhuận mỗi CP",
                "B. Lợi nhuận tăng 20%",
                "C. Cổ tức 20%",
                "D. Doanh thu gấp 20 lần",
            ],
            "answer": "A",
            "explanation": "P/E = Price / EPS. P/E = 20 nghĩa là nhà đầu tư trả 20đ cho 1đ lợi nhuận.",
        },
        {
            "question": "ROE cao nhưng D/E cũng rất cao. Đánh giá thế nào?",
            "options": [
                "A. Doanh nghiệp tuyệt vời",
                "B. ROE cao nhờ đòn bẩy tài chính, rủi ro cao",
                "C. Nên mua ngay",
                "D. D/E không liên quan đến ROE",
            ],
            "answer": "B",
            "explanation": "ROE = Net Income / Equity. Khi D/E cao, Equity thấp → ROE bị 'thổi' lên nhờ đòn bẩy, không phải năng lực thực sự. Phân tích Dupont để hiểu rõ.",
        },
        {
            "question": "Doanh nghiệp có lợi nhuận tăng nhưng dòng tiền hoạt động âm. Red flag?",
            "options": [
                "A. Không sao, lợi nhuận mới quan trọng",
                "B. Có thể là red flag - cần kiểm tra phải thu và hàng tồn kho",
                "C. Dòng tiền âm luôn là xấu",
                "D. Chỉ cần P/E thấp là được",
            ],
            "answer": "B",
            "explanation": "Lãi trên giấy nhưng không thu được tiền thực → cần kiểm tra khoản phải thu, hàng tồn kho, và chất lượng doanh thu.",
        },
        {
            "question": "Margin of Safety trong đầu tư giá trị là gì?",
            "options": [
                "A. Biên lợi nhuận gộp",
                "B. Khoảng cách giữa giá thị trường và giá trị nội tại",
                "C. Tỷ lệ margin tại CTCK",
                "D. Mức stop loss",
            ],
            "answer": "B",
            "explanation": "Margin of Safety = (Giá trị nội tại - Giá thị trường) / Giá trị nội tại. Chỉ mua khi giá thấp hơn giá trị 20-30%.",
        },
        {
            "question": "Free Cash Flow (FCF) quan trọng vì?",
            "options": [
                "A. FCF là tiền thực sự DN có thể dùng trả cổ tức, mua lại CP, hoặc tái đầu tư",
                "B. FCF = Doanh thu",
                "C. FCF luôn bằng lợi nhuận",
                "D. FCF không quan trọng",
            ],
            "answer": "A",
            "explanation": "FCF = CF hoạt động - CapEx. Đây là tiền 'thực' mà DN tạo ra sau khi đầu tư, có thể dùng trả cổ tức, giảm nợ, hoặc tái đầu tư.",
        },
    ],
    "technical": [
        {
            "question": "RSI = 25 nghĩa là gì?",
            "options": [
                "A. Cổ phiếu đang trong vùng quá bán (oversold)",
                "B. Cổ phiếu đang trong vùng quá mua",
                "C. Xu hướng tăng mạnh",
                "D. Nên bán ngay",
            ],
            "answer": "A",
            "explanation": "RSI < 30 = oversold. Cổ phiếu đã giảm quá nhiều, có thể phục hồi. Tuy nhiên, cần xác nhận bằng các tín hiệu khác.",
        },
        {
            "question": "MACD cắt lên Signal Line. Đây là tín hiệu gì?",
            "options": [
                "A. Tín hiệu bán",
                "B. Tín hiệu mua (bullish crossover)",
                "C. Không có ý nghĩa",
                "D. Nên chờ thêm RSI > 80",
            ],
            "answer": "B",
            "explanation": "MACD cắt lên Signal Line = Bullish crossover, báo hiệu đà tăng. Xác nhận bằng volume tăng sẽ đáng tin hơn.",
        },
        {
            "question": "Golden Cross là gì?",
            "options": [
                "A. SMA(50) cắt lên SMA(200)",
                "B. RSI > 70",
                "C. MACD > 0",
                "D. Giá vượt Bollinger band trên",
            ],
            "answer": "A",
            "explanation": "Golden Cross: SMA(50) cắt lên SMA(200) → tín hiệu tăng dài hạn. Ngược lại là Death Cross.",
        },
        {
            "question": "Bollinger Bands thu hẹp (squeeze) báo hiệu gì?",
            "options": [
                "A. Thị trường sắp nghỉ",
                "B. Chuẩn bị có biến động mạnh (breakout)",
                "C. Nên bán cổ phiếu",
                "D. Volume sẽ giảm",
            ],
            "answer": "B",
            "explanation": "Bollinger squeeze = biến động thấp kéo dài → tích luỹ năng lượng. Breakout (lên hoặc xuống) thường xảy ra sau đó.",
        },
    ],
    "trading": [
        {
            "question": "Rule 2% trong quản lý vốn nghĩa là gì?",
            "options": [
                "A. Lãi 2% thì bán",
                "B. Chỉ rủi ro tối đa 2% tổng vốn trên 1 lệnh",
                "C. Mua 2% vốn vào 1 CP",
                "D. Phí giao dịch 2%",
            ],
            "answer": "B",
            "explanation": "Rule 2%: (Entry - Stop Loss) × Số CP ≤ 2% tổng vốn. Giúp bảo toàn vốn khi thua lỗ liên tiếp.",
        },
        {
            "question": "R:R = 1:3 nghĩa là?",
            "options": [
                "A. Rủi ro gấp 3 lần lợi nhuận",
                "B. Lợi nhuận tiềm năng gấp 3 lần rủi ro",
                "C. Mua 3 lô",
                "D. Giữ 3 ngày",
            ],
            "answer": "B",
            "explanation": "Risk:Reward 1:3 → chấp nhận rủi ro 1 phần để kiếm 3 phần. Win rate 33% cũng đủ hoà vốn.",
        },
        {
            "question": "Lệnh ATC trên HOSE là gì?",
            "options": [
                "A. Lệnh mở cửa, khớp giá mở cửa",
                "B. Lệnh đóng cửa, khớp giá đóng cửa 14:30-14:45",
                "C. Lệnh giới hạn",
                "D. Lệnh huỷ",
            ],
            "answer": "B",
            "explanation": "ATC = At The Close. Đặt trong phiên 14:30-14:45, khớp tại giá đóng cửa duy nhất.",
        },
        {
            "question": "Call margin xảy ra khi nào?",
            "options": [
                "A. Khi muốn mua thêm CP",
                "B. Khi tỷ lệ equity/position value giảm dưới mức duy trì (30-35%)",
                "C. Khi giá CP tăng mạnh",
                "D. Khi hết hạn margin",
            ],
            "answer": "B",
            "explanation": "Call margin khi equity/value < maintenance ratio (~30-35%). Phải nộp thêm tiền hoặc bán bớt CP trong 1-3 ngày, nếu không CTCK sẽ force sell.",
        },
    ],
}


class EducationTool(BaseTool):
    """
    Công cụ giáo dục tài chính & chứng khoán cho nhà đầu tư Việt Nam:
    - Tra cứu thuật ngữ chứng khoán
    - Hướng dẫn / Tutorial theo chủ đề
    - Case study phân tích cổ phiếu
    - Liệt kê thuật ngữ theo nhóm
    - Quiz kiểm tra kiến thức
    """

    def get_name(self) -> str:
        return "education"

    def get_description(self) -> str:
        return (
            "Kiến thức đầu tư chứng khoán Việt Nam: giải thích thuật ngữ "
            "(P/E, RSI, MACD, ...), hướng dẫn cho người mới, "
            "tutorial phân tích cơ bản / kỹ thuật, quiz kiểm tra kiến thức. "
            "Actions: define, tutorial, case_study, list_terms, quiz."
        )

    async def run(self, action: str = "define", **kwargs) -> Dict[str, Any]:
        """
        Actions:
            define      - Giải thích thuật ngữ
            tutorial    - Hướng dẫn / bài học theo chủ đề
            case_study  - Case study phân tích CP
            list_terms  - Liệt kê thuật ngữ theo nhóm
            quiz        - Câu hỏi kiểm tra kiến thức
        """
        action_map = {
            "define": self.get_term_definition,
            "tutorial": self.get_tutorial,
            "case_study": self.get_case_study,
            "list_terms": self.list_terms,
            "quiz": self.get_quiz,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. "
                         f"Sử dụng: {list(action_map.keys())}",
            }

        try:
            return await action_map[action](**kwargs)
        except Exception as e:
            logger.error(f"Education '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": f"Lỗi: {str(e)}"}

    # =================================================================
    # 1. DEFINE - Giải thích thuật ngữ
    # =================================================================

    async def get_term_definition(
        self,
        term: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tra cứu thuật ngữ chứng khoán.

        Args:
            term: Thuật ngữ cần tra cứu (vd: "P/E", "RSI", "margin")
        """
        if not term:
            return {"success": False, "error": "Cần cung cấp thuật ngữ (term)."}

        term_key = term.lower().strip().replace(" ", "_")

        # Direct match
        if term_key in TERM_DATABASE:
            entry = TERM_DATABASE[term_key]
            return self._format_term_result(entry)

        # Fuzzy search: check if term appears in key, term name, or definition
        matches = []
        for key, entry in TERM_DATABASE.items():
            search_text = f"{key} {entry['term']} {entry.get('vi', '')} {entry['definition']}".lower()
            if term.lower() in search_text:
                matches.append(entry)

        if matches:
            if len(matches) == 1:
                return self._format_term_result(matches[0])
            else:
                return {
                    "success": True,
                    "data": {
                        "search_term": term,
                        "matches_found": len(matches),
                        "results": [
                            {
                                "term": m["term"],
                                "vi": m.get("vi", ""),
                                "short_definition": m["definition"][:120] + "...",
                            }
                            for m in matches
                        ],
                    },
                    "summary": (
                        f"Tìm thấy {len(matches)} thuật ngữ liên quan đến '{term}': "
                        + ", ".join(m["term"] for m in matches)
                        + ". Hãy hỏi cụ thể hơn để xem chi tiết."
                    ),
                }

        # Not found – list available categories
        categories = set(e["category"] for e in TERM_DATABASE.values())
        all_terms = [e["term"] for e in TERM_DATABASE.values()]
        return {
            "success": False,
            "error": f"Không tìm thấy thuật ngữ '{term}'.",
            "available_categories": sorted(categories),
            "available_terms": all_terms,
            "suggestion": "Hãy thử tìm với từ khóa khác hoặc dùng action 'list_terms' để xem danh sách.",
        }

    def _format_term_result(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single term entry."""
        return {
            "success": True,
            "data": {
                "term": entry["term"],
                "category": entry["category"],
                "vi": entry.get("vi", ""),
                "definition": entry["definition"],
                "formula": entry.get("formula", ""),
                "interpretation": entry.get("interpretation", []),
                "vietnam_context": entry.get("vietnam_context", ""),
                "example": entry.get("example", ""),
                "related_terms": entry.get("related", []),
            },
            "summary": (
                f"**{entry['term']}** ({entry.get('vi', '')})\n\n"
                f"{entry['definition']}\n\n"
                f"📐 Công thức: {entry.get('formula', 'N/A')}\n\n"
                f"📖 Cách đọc:\n"
                + "\n".join(f"• {i}" for i in entry.get("interpretation", []))
                + f"\n\n🇻🇳 VN: {entry.get('vietnam_context', '')}"
                + f"\n\n💡 Ví dụ: {entry.get('example', '')}"
            ),
        }

    # =================================================================
    # 2. TUTORIAL - Hướng dẫn theo chủ đề
    # =================================================================

    async def get_tutorial(
        self,
        topic: str = "beginner",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Lấy hướng dẫn / bài học theo chủ đề.

        Args:
            topic: Chủ đề (beginner, fundamental_analysis, technical_analysis,
                   risk_management, value_investing, swing_trading, dca,
                   reading_financial_statements)
        """
        topic_key = topic.lower().strip().replace(" ", "_")

        # Fuzzy match
        found_key = None
        for key in TUTORIAL_DATABASE:
            if topic_key in key or key in topic_key:
                found_key = key
                break

        # Keyword search
        if not found_key:
            keyword_map = {
                "mới": "beginner", "bắt đầu": "beginner", "newbie": "beginner",
                "cơ bản": "fundamental_analysis", "fundamental": "fundamental_analysis",
                "kỹ thuật": "technical_analysis", "technical": "technical_analysis",
                "rủi ro": "risk_management", "risk": "risk_management",
                "giá trị": "value_investing", "value": "value_investing",
                "swing": "swing_trading",
                "dca": "dca", "trung bình": "dca",
                "bctc": "reading_financial_statements", "tài chính": "reading_financial_statements",
                "báo cáo": "reading_financial_statements",
            }
            for kw, key in keyword_map.items():
                if kw in topic_key:
                    found_key = key
                    break

        if not found_key:
            available = {k: v["title"] for k, v in TUTORIAL_DATABASE.items()}
            return {
                "success": False,
                "error": f"Không tìm thấy tutorial cho '{topic}'.",
                "available_topics": available,
                "suggestion": "Chọn 1 trong các chủ đề trên.",
            }

        tutorial = TUTORIAL_DATABASE[found_key]
        sections_text = []
        for sec in tutorial["sections"]:
            sections_text.append(f"### {sec['title']}\n{sec['content']}")

        return {
            "success": True,
            "data": {
                "topic": found_key,
                "title": tutorial["title"],
                "category": tutorial["category"],
                "sections": tutorial["sections"],
                "total_sections": len(tutorial["sections"]),
            },
            "summary": (
                f"## {tutorial['title']}\n\n"
                + "\n\n".join(sections_text)
            ),
        }

    # =================================================================
    # 3. CASE STUDY - Phân tích CP mẫu
    # =================================================================

    async def get_case_study(
        self,
        symbol: str = "VNM",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo case study phân tích cho 1 mã CP dựa trên framework.

        Args:
            symbol: Mã cổ phiếu (VNM, FPT, VCB, HPG, ...)
        """
        symbol = symbol.upper().strip()
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã CP (symbol)."}

        # Case study framework (template)
        case_study = {
            "symbol": symbol,
            "title": f"📋 Case Study: Phân tích {symbol}",
            "framework": [
                {
                    "step": "1. Tổng quan doanh nghiệp",
                    "questions": [
                        f"{symbol} kinh doanh gì? Thuộc ngành nào?",
                        "Mô hình kinh doanh? Nguồn doanh thu chính?",
                        "Lợi thế cạnh tranh (Moat)?",
                        "Ban lãnh đạo có năng lực?",
                    ],
                    "tools_to_use": ["vnstock_connector → get_stock_overview"],
                },
                {
                    "step": "2. Phân tích tài chính",
                    "questions": [
                        "Doanh thu & lợi nhuận tăng trưởng ra sao (3-5 năm)?",
                        "ROE, ROA, margins xu hướng thế nào?",
                        "Cấu trúc nợ có an toàn? D/E?",
                        "Dòng tiền hoạt động có dương không? FCF?",
                    ],
                    "tools_to_use": [
                        "financial_statements → summary",
                        "financial_ratios → all",
                    ],
                },
                {
                    "step": "3. Định giá",
                    "questions": [
                        "P/E hiện tại so với trung bình lịch sử và ngành?",
                        "P/B so với ROE có hợp lý?",
                        "DCF cho giá trị nội tại bao nhiêu?",
                        "Margin of Safety?",
                    ],
                    "tools_to_use": ["dcf_valuation → valuation"],
                },
                {
                    "step": "4. Phân tích kỹ thuật",
                    "questions": [
                        "Xu hướng hiện tại? (uptrend/downtrend/sideways)",
                        "RSI, MACD cho tín hiệu gì?",
                        "Các mức hỗ trợ/kháng cự quan trọng?",
                        "Volume có xác nhận xu hướng?",
                    ],
                    "tools_to_use": [
                        "technical_indicators → summary",
                        "trading_signals → recommendation",
                    ],
                },
                {
                    "step": "5. Rủi ro",
                    "questions": [
                        "Rủi ro ngành? Rủi ro điều hành?",
                        "Altman Z-Score? Sức khoẻ tài chính?",
                        "Rủi ro vĩ mô ảnh hưởng?",
                    ],
                    "tools_to_use": ["company_risk → assessment"],
                },
                {
                    "step": "6. Kết luận & Hành động",
                    "questions": [
                        "Nên MUA / GIỮ / BÁN? Tại sao?",
                        "Giá mua vào hợp lý?",
                        "Stop loss đặt ở đâu?",
                        "Target và thời gian nắm giữ?",
                    ],
                    "tools_to_use": ["Tổng hợp tất cả tool trên"],
                },
            ],
            "tip": (
                f"💡 Sử dụng lệnh: 'phân tích {symbol}' để Dexter tự động "
                f"chạy tất cả các tool và tổng hợp kết quả."
            ),
        }

        # Format summary
        summary_parts = [f"## 📋 Case Study Framework: Phân tích {symbol}\n"]
        for step_info in case_study["framework"]:
            summary_parts.append(f"\n### {step_info['step']}")
            for q in step_info["questions"]:
                summary_parts.append(f"  ❓ {q}")
            summary_parts.append(f"  🔧 Tools: {', '.join(step_info['tools_to_use'])}")

        summary_parts.append(f"\n{case_study['tip']}")

        return {
            "success": True,
            "data": case_study,
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 4. LIST TERMS - Liệt kê thuật ngữ theo nhóm
    # =================================================================

    async def list_terms(
        self,
        category: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Liệt kê thuật ngữ theo nhóm.

        Args:
            category: Nhóm (fundamental, technical, trading). 
                      Để trống = tất cả.
        """
        categories: Dict[str, List[Dict[str, str]]] = {}

        for key, entry in TERM_DATABASE.items():
            cat = entry["category"]
            if category and cat != category.lower().strip():
                continue
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "key": key,
                "term": entry["term"],
                "vi": entry.get("vi", ""),
            })

        if not categories:
            all_cats = sorted(set(e["category"] for e in TERM_DATABASE.values()))
            return {
                "success": False,
                "error": f"Không tìm thấy category '{category}'.",
                "available_categories": all_cats,
            }

        total = sum(len(v) for v in categories.values())

        # Build summary
        summary_parts = ["## 📚 Danh sách Thuật ngữ Chứng khoán\n"]
        cat_labels = {
            "fundamental": "📊 Phân tích Cơ bản",
            "technical": "📈 Phân tích Kỹ thuật",
            "trading": "💹 Giao dịch",
        }
        for cat, terms in sorted(categories.items()):
            label = cat_labels.get(cat, cat.capitalize())
            summary_parts.append(f"\n### {label} ({len(terms)} thuật ngữ)")
            for t in terms:
                summary_parts.append(f"  • **{t['term']}** — {t['vi']}")

        summary_parts.append(f"\nTổng: {total} thuật ngữ. Dùng action 'define' để xem chi tiết.")

        return {
            "success": True,
            "data": {
                "categories": categories,
                "total_terms": total,
                "filter": category if category else "all",
            },
            "summary": "\n".join(summary_parts),
        }

    # =================================================================
    # 5. QUIZ - Kiểm tra kiến thức
    # =================================================================

    async def get_quiz(
        self,
        topic: str = "fundamental",
        num_questions: int = 3,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo quiz kiểm tra kiến thức.

        Args:
            topic: Chủ đề (fundamental, technical, trading) hoặc 'all'
            num_questions: Số câu hỏi (mặc định 3)
        """
        topic_lower = topic.lower().strip()

        if topic_lower == "all" or topic_lower == "":
            all_questions = []
            for questions in QUIZ_DATABASE.values():
                all_questions.extend(questions)
        elif topic_lower in QUIZ_DATABASE:
            all_questions = QUIZ_DATABASE[topic_lower]
        else:
            return {
                "success": False,
                "error": f"Không tìm thấy quiz cho '{topic}'.",
                "available_topics": list(QUIZ_DATABASE.keys()) + ["all"],
            }

        # Select random questions
        num_questions = min(num_questions, len(all_questions))
        selected = random.sample(all_questions, num_questions)

        # Format
        quiz_items = []
        summary_parts = [f"## 🧠 Quiz: Kiểm tra Kiến thức ({topic})\n"]

        for i, q in enumerate(selected, 1):
            quiz_items.append({
                "number": i,
                "question": q["question"],
                "options": q["options"],
                "answer": q["answer"],
                "explanation": q["explanation"],
            })
            summary_parts.append(f"### Câu {i}: {q['question']}")
            for opt in q["options"]:
                summary_parts.append(f"  {opt}")
            summary_parts.append("")

        # Answers section
        summary_parts.append("\n---\n### 📝 Đáp án:")
        for item in quiz_items:
            summary_parts.append(
                f"**Câu {item['number']}**: {item['answer']} — {item['explanation']}"
            )

        return {
            "success": True,
            "data": {
                "topic": topic,
                "num_questions": num_questions,
                "questions": quiz_items,
            },
            "summary": "\n".join(summary_parts),
        }
