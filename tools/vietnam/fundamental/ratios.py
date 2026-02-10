
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from dexter_vietnam.tools.vietnam.fundamental.financial_statements import FinancialStatementsTool
from typing import Dict, Any, Optional, List, Tuple
import math


class FinancialRatiosTool(BaseTool):

    # Ngưỡng đánh giá chỉ số
    THRESHOLDS = {
        'pe': {'cheap': 10, 'fair': 15, 'expensive': 25},
        'pb': {'cheap': 1.0, 'fair': 2.0, 'expensive': 5.0},
        'roe': {'low': 0.10, 'good': 0.15, 'excellent': 0.25},
        'roa': {'low': 0.05, 'good': 0.08, 'excellent': 0.15},
        'debt_equity': {'safe': 0.5, 'moderate': 1.0, 'risky': 2.0},
        'current_ratio': {'danger': 1.0, 'safe': 1.5, 'strong': 2.5},
        'gross_margin': {'low': 0.15, 'good': 0.30, 'excellent': 0.50},
        'net_margin': {'low': 0.05, 'good': 0.10, 'excellent': 0.20},
    }

    def __init__(self):
        self._data_tool = VnstockTool()
        self._fs_tool = FinancialStatementsTool()

    def get_name(self) -> str:
        return "financial_ratios"

    def get_description(self) -> str:
        return (
            "Tính toán và đánh giá chỉ số tài chính: P/E, P/B, ROE, ROA, "
            "Debt/Equity, Current Ratio, EPS, BVPS, Margins."
        )

    async def run(self, action: str = "all", symbol: str = "", **kwargs) -> Dict[str, Any]:

        action_map = {
            'all': self.get_all_ratios,
            'valuation': self.get_valuation_ratios,
            'profitability': self.get_profitability_ratios,
            'liquidity': self.get_liquidity_ratios,
            'leverage': self.get_leverage_ratios,
            'per_share': self.get_per_share_ratios,
            'compare': self.get_ratio_comparison,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        if not symbol:
            return {"success": False, "error": "Symbol không được để trống"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    async def _fetch_ratios(self, symbol: str, period: str = 'quarter') -> List[Dict]:
        """Lấy raw ratios từ vnstock (đã có MultiIndex)."""
        result = await self._data_tool.get_financial_ratio(symbol, period)
        if not result.get("success"):
            raise ValueError(result.get("error", "Không lấy được chỉ số tài chính"))
        return result["data"]

    def _flatten_ratio(self, row: Dict) -> Dict[str, Any]:
        """Flatten MultiIndex tuple-keys → simple keys."""
        flat = {}
        for key, val in row.items():
            if isinstance(key, tuple):
                group, name = key
                flat[name] = val
            else:
                flat[key] = val
        return flat

    def _safe_round(self, val: Any, decimals: int = 4) -> Any:
        """Round an toàn, trả về None nếu không phải số."""
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return None
        try:
            return round(float(val), decimals)
        except (TypeError, ValueError):
            return val

    def _assess(self, metric: str, value: Any) -> str:
        """Đánh giá một chỉ số theo ngưỡng."""
        if value is None:
            return "N/A"
        thresholds = self.THRESHOLDS.get(metric)
        if not thresholds:
            return ""

        v = float(value)
        keys = list(thresholds.keys())

        # Các chỉ số "càng thấp càng tốt" (P/E, P/B, D/E)
        if metric in ('pe', 'pb', 'debt_equity'):
            if v <= thresholds[keys[0]]:
                return f"Tốt (≤{thresholds[keys[0]]})"
            elif v <= thresholds[keys[1]]:
                return f"Hợp lý ({thresholds[keys[0]]}-{thresholds[keys[1]]})"
            else:
                return f"Cao (>{thresholds[keys[1]]})"
        # Các chỉ số "càng cao càng tốt" (ROE, ROA, Margins, Current Ratio)
        else:
            if v >= thresholds[keys[2]]:
                return f"Xuất sắc (≥{thresholds[keys[2]]})"
            elif v >= thresholds[keys[1]]:
                return f"Tốt (≥{thresholds[keys[1]]})"
            else:
                return f"Thấp (<{thresholds[keys[1]]})"


    async def get_all_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        """Trả về tất cả chỉ số + đánh giá cho năm gần nhất."""
        raw_list = await self._fetch_ratios(symbol)
        if not raw_list:
            return {"success": False, "error": "Không có dữ liệu"}

        flat = self._flatten_ratio(raw_list[0])
        r = self._safe_round

        ratios = {
            "year": flat.get("Năm"),
            "valuation": {
                "pe": {"value": r(flat.get("P/E")), "assessment": self._assess("pe", flat.get("P/E"))},
                "pb": {"value": r(flat.get("P/B")), "assessment": self._assess("pb", flat.get("P/B"))},
                "ps": {"value": r(flat.get("P/S"))},
                "p_cash_flow": {"value": r(flat.get("P/Cash Flow"))},
                "ev_ebitda": {"value": r(flat.get("EV/EBITDA"))},
                "market_cap_billion": {"value": r(flat.get("Vốn hóa (Tỷ đồng)"))},
            },
            "profitability": {
                "roe": {"value": r(flat.get("ROE (%)")), "assessment": self._assess("roe", flat.get("ROE (%)"))},
                "roa": {"value": r(flat.get("ROA (%)")), "assessment": self._assess("roa", flat.get("ROA (%)"))},
                "roic": {"value": r(flat.get("ROIC (%)"))},
                "gross_margin": {"value": r(flat.get("Biên lợi nhuận gộp (%)")), "assessment": self._assess("gross_margin", flat.get("Biên lợi nhuận gộp (%)"))},
                "net_margin": {"value": r(flat.get("Biên lợi nhuận ròng (%)")), "assessment": self._assess("net_margin", flat.get("Biên lợi nhuận ròng (%)"))},
                "ebit_margin": {"value": r(flat.get("Biên EBIT (%)"))},
                "dividend_yield": {"value": r(flat.get("Tỷ suất cổ tức (%)"))},
            },
            "liquidity": {
                "current_ratio": {"value": r(flat.get("Chỉ số thanh toán hiện thời")), "assessment": self._assess("current_ratio", flat.get("Chỉ số thanh toán hiện thời"))},
                "quick_ratio": {"value": r(flat.get("Chỉ số thanh toán nhanh"))},
                "cash_ratio": {"value": r(flat.get("Chỉ số thanh toán tiền mặt"))},
                "interest_coverage": {"value": r(flat.get("Khả năng chi trả lãi vay"))},
            },
            "leverage": {
                "debt_equity": {"value": r(flat.get("Nợ/VCSH")), "assessment": self._assess("debt_equity", flat.get("Nợ/VCSH"))},
                "debt_short_long_equity": {"value": r(flat.get("(Vay NH+DH)/VCSH"))},
                "financial_leverage": {"value": r(flat.get("Đòn bẩy tài chính"))},
                "fixed_assets_equity": {"value": r(flat.get("TSCĐ / Vốn CSH"))},
            },
            "per_share": {
                "eps": {"value": r(flat.get("EPS (VND)"), 0)},
                "bvps": {"value": r(flat.get("BVPS (VND)"), 0)},
                "shares_outstanding_million": {"value": r(flat.get("Số CP lưu hành (Triệu CP)"))},
            },
            "efficiency": {
                "asset_turnover": {"value": r(flat.get("Vòng quay tài sản"))},
                "fixed_asset_turnover": {"value": r(flat.get("Vòng quay TSCĐ"))},
                "inventory_turnover": {"value": r(flat.get("Vòng quay hàng tồn kho"))},
                "days_receivable": {"value": r(flat.get("Số ngày thu tiền bình quân"))},
                "days_inventory": {"value": r(flat.get("Số ngày tồn kho bình quân"))},
                "days_payable": {"value": r(flat.get("Số ngày thanh toán bình quân"))},
                "cash_cycle": {"value": r(flat.get("Chu kỳ tiền"))},
            },
        }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "all_ratios",
            "data": ratios,
        }


    async def get_valuation_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        result = await self.get_all_ratios(symbol)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "valuation",
            "data": result["data"]["valuation"],
            "year": result["data"]["year"],
        }

    async def get_profitability_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        result = await self.get_all_ratios(symbol)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "profitability",
            "data": result["data"]["profitability"],
            "year": result["data"]["year"],
        }

    async def get_liquidity_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        result = await self.get_all_ratios(symbol)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "liquidity",
            "data": result["data"]["liquidity"],
            "year": result["data"]["year"],
        }

    async def get_leverage_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        result = await self.get_all_ratios(symbol)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "leverage",
            "data": result["data"]["leverage"],
            "year": result["data"]["year"],
        }

    async def get_per_share_ratios(self, symbol: str, **_) -> Dict[str, Any]:
        result = await self.get_all_ratios(symbol)
        if not result.get("success"):
            return result
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "per_share",
            "data": result["data"]["per_share"],
            "year": result["data"]["year"],
        }


    async def get_ratio_comparison(
        self, symbol: str, years: int = 3, **_
    ) -> Dict[str, Any]:
        """So sánh chỉ số tài chính qua các năm."""
        raw_list = await self._fetch_ratios(symbol)
        if not raw_list:
            return {"success": False, "error": "Không có dữ liệu"}

        # Lấy nhiều năm
        comparison = []
        for row in raw_list[:years]:
            flat = self._flatten_ratio(row)
            r = self._safe_round
            comparison.append({
                "year": flat.get("Năm"),
                "pe": r(flat.get("P/E")),
                "pb": r(flat.get("P/B")),
                "roe": r(flat.get("ROE (%)")),
                "roa": r(flat.get("ROA (%)")),
                "gross_margin": r(flat.get("Biên lợi nhuận gộp (%)")),
                "net_margin": r(flat.get("Biên lợi nhuận ròng (%)")),
                "debt_equity": r(flat.get("Nợ/VCSH")),
                "current_ratio": r(flat.get("Chỉ số thanh toán hiện thời")),
                "eps": r(flat.get("EPS (VND)"), 0),
                "bvps": r(flat.get("BVPS (VND)"), 0),
                "dividend_yield": r(flat.get("Tỷ suất cổ tức (%)")),
            })

        # Tính trend (xu hướng )
        trends = {}
        if len(comparison) >= 2:
            curr = comparison[0]
            prev = comparison[1]
            for key in ['roe', 'roa', 'gross_margin', 'net_margin', 'eps']:
                c = curr.get(key)
                p = prev.get(key)
                if c is not None and p is not None and p != 0:
                    change = round((c - p) / abs(p), 4)
                    direction = "↑" if change > 0.01 else ("↓" if change < -0.01 else "→")
                    trends[key] = {"change": change, "direction": direction}

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "ratio_comparison",
            "data": comparison,
            "trends": trends,
        }


    async def calculate_from_statements(
        self, symbol: str, market_price: Optional[float] = None, **_
    ) -> Dict[str, Any]:
 
        # Lấy BCTC
        summary = await self._fs_tool.get_financial_summary(symbol)
        if not summary.get("success"):
            return summary

        data = summary["data"]
        r = self._safe_round

        # Lấy giá thị trường nếu chưa có
        if market_price is None:
            price_result = await self._data_tool.get_stock_price(symbol)
            if price_result.get("success") and price_result["data"]:
                market_price = price_result["data"][-1].get("close", 0) * 1000  # về đồng
            else:
                market_price = 0

        # Giá trị cần thiết (tỷ đồng → đồng)
        total_assets = (data.get("total_assets") or 0) * 1e9
        total_equity = (data.get("total_equity") or 0) * 1e9
        total_liabilities = (data.get("total_liabilities") or 0) * 1e9
        current_assets = (data.get("total_assets") or 0) * 1e9  # approx
        net_revenue = (data.get("net_revenue") or 0) * 1e9
        gross_profit = (data.get("gross_profit") or 0) * 1e9
        net_income = (data.get("net_income") or 0) * 1e9

        calculated = {
            "year": data.get("year"),
            "market_price": market_price,
        }

        # ROE = Net Income / Equity
        if total_equity > 0:
            calculated["roe"] = r(net_income / total_equity)

        # ROA = Net Income / Total Assets
        if total_assets > 0:
            calculated["roa"] = r(net_income / total_assets)

        # Debt/Equity
        if total_equity > 0:
            calculated["debt_equity"] = r(total_liabilities / total_equity)

        # Gross Margin
        if net_revenue > 0:
            calculated["gross_margin"] = r(gross_profit / net_revenue)
            calculated["net_margin"] = r(net_income / net_revenue)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "calculated_ratios",
            "note": "Tính từ BCTC, có thể lệch nhỏ so với API",
            "data": calculated,
        }
