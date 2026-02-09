"""
Module 2.3: DCF Valuation
Định giá cổ phiếu bằng phương pháp chiết khấu dòng tiền (Discounted Cash Flow)

Theo CODING_ROADMAP.md - Module 2

Formula: DCF = Σ(FCF_t / (1+WACC)^t) + Terminal Value / (1+WACC)^n
"""
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from dexter_vietnam.tools.vietnam.fundamental.financial_statements import FinancialStatementsTool
from typing import Dict, Any, Optional, List
import math


class DCFValuationTool(BaseTool):
    """
    Định giá cổ phiếu bằng phương pháp DCF.

    Các bước:
    1. Tính WACC (Weighted Average Cost of Capital)
    2. Dự báo Free Cash Flow (5-10 năm)
    3. Tính Terminal Value
    4. Chiết khấu về hiện tại → Intrinsic Value per share
    """

    # Tham số mặc định cho thị trường Việt Nam
    DEFAULTS = {
        'risk_free_rate': 0.045,       # Lãi suất TPCP VN 10 năm ~4.5%
        'market_return': 0.12,         # Kỳ vọng lợi nhuận TTCK VN ~12%
        'beta': 1.0,                   # Beta mặc định
        'tax_rate': 0.20,              # Thuế TNDN 20%
        'cost_of_debt': 0.08,          # Chi phí vay trung bình ~8%
        'terminal_growth': 0.03,       # Tăng trưởng vĩnh viễn ~3% (≈ GDP dài hạn)
        'projection_years': 5,         # Số năm dự báo
        'fcf_growth_rate': None,       # None = tự tính từ lịch sử
        'margin_of_safety': 0.25,      # Biên an toàn 25%
    }

    def __init__(self):
        self._data_tool = VnstockTool()
        self._fs_tool = FinancialStatementsTool()

    def get_name(self) -> str:
        return "dcf_valuation"

    def get_description(self) -> str:
        return (
            "Định giá cổ phiếu bằng DCF (Discounted Cash Flow). "
            "Tính WACC, dự báo FCF, Terminal Value → Intrinsic Value."
        )

    async def run(self, symbol: str, action: str = "valuation", **kwargs) -> Dict[str, Any]:
        """
        Args:
            symbol: Mã cổ phiếu
            action: Hành động
                - valuation: Định giá DCF đầy đủ (mặc định)
                - wacc: Chỉ tính WACC
                - sensitivity: Phân tích độ nhạy
            **kwargs: Ghi đè các tham số mặc định
                - risk_free_rate, market_return, beta, tax_rate,
                  cost_of_debt, terminal_growth, projection_years,
                  fcf_growth_rate, margin_of_safety
        """
        action_map = {
            'valuation': self.run_dcf_valuation,
            'wacc': self.calculate_wacc_only,
            'sensitivity': self.sensitivity_analysis,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===================================================================
    # Helpers
    # ===================================================================

    def _get_params(self, **overrides) -> Dict[str, Any]:
        """Lấy tham số, cho phép ghi đè."""
        params = dict(self.DEFAULTS)
        for k, v in overrides.items():
            if k in params and v is not None:
                params[k] = v
        return params

    def _calc_wacc(
        self,
        equity_value: float,
        debt_value: float,
        cost_of_equity: float,
        cost_of_debt: float,
        tax_rate: float,
    ) -> float:
        """
        WACC = (E/V × Re) + (D/V × Rd × (1 - Tax))
        """
        total = equity_value + debt_value
        if total <= 0:
            return cost_of_equity  # fallback

        weight_equity = equity_value / total
        weight_debt = debt_value / total

        wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
        return round(wacc, 4)

    def _calc_cost_of_equity(
        self, risk_free: float, beta: float, market_return: float
    ) -> float:
        """CAPM: Re = Rf + β × (Rm − Rf)"""
        return risk_free + beta * (market_return - risk_free)

    def _project_fcf(
        self,
        base_fcf: float,
        growth_rate: float,
        years: int,
    ) -> List[Dict[str, Any]]:
        """Dự báo FCF cho n năm tới."""
        projections = []
        fcf = base_fcf
        for year in range(1, years + 1):
            fcf = fcf * (1 + growth_rate)
            projections.append({
                "year": year,
                "fcf": round(fcf, 2),
                "growth_rate": growth_rate,
            })
        return projections

    def _calc_terminal_value(
        self, final_fcf: float, terminal_growth: float, wacc: float
    ) -> float:
        """
        Terminal Value = FCF_final × (1 + g) / (WACC − g)
        Gordon Growth Model
        """
        if wacc <= terminal_growth:
            # Tránh chia cho 0 hoặc âm
            return final_fcf * 20  # fallback: 20x earnings
        return final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

    def _discount(self, value: float, wacc: float, year: int) -> float:
        """Chiết khấu giá trị về hiện tại."""
        return value / ((1 + wacc) ** year)

    # ===================================================================
    # 1. FULL DCF VALUATION
    # ===================================================================

    async def run_dcf_valuation(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Bước 1: Lấy dữ liệu → Bước 2: Tính WACC → Bước 3: Dự báo FCF →
        Bước 4: Terminal Value → Bước 5: Intrinsic Value per share

        Returns:
            {
                "success": True,
                "symbol": str,
                "data": {
                    "wacc": float,
                    "base_fcf": float,
                    "fcf_growth_rate": float,
                    "projected_fcf": [...],
                    "terminal_value": float,
                    "enterprise_value": float,
                    "equity_value": float,
                    "intrinsic_value_per_share": float,
                    "market_price": float,
                    "upside": float,
                    "recommendation": str,
                }
            }
        """
        params = self._get_params(**kwargs)

        # ---- Bước 1: Lấy dữ liệu tài chính ----
        cf_result = await self._fs_tool.get_cash_flow(symbol, years=5)
        bs_result = await self._fs_tool.get_balance_sheet(symbol, years=2)

        if not cf_result.get("success") or not bs_result.get("success"):
            return {"success": False, "error": "Không lấy được dữ liệu tài chính"}

        cf_data = cf_result["data"]
        bs_data = bs_result["data"]

        if not cf_data or not bs_data:
            return {"success": False, "error": "Dữ liệu tài chính trống"}

        # Free Cash Flow gần nhất (tỷ đồng)
        base_fcf = cf_data[0].get("free_cash_flow", 0)
        if base_fcf is None or base_fcf <= 0:
            # Fallback: dùng CFO nếu FCF âm
            base_fcf = cf_data[0].get("cfo", 0) or 1

        # Tính FCF growth rate trung bình từ lịch sử
        fcf_growth = params['fcf_growth_rate']
        if fcf_growth is None:
            fcf_values = [d.get("free_cash_flow", 0) or 0 for d in cf_data]
            fcf_values = [v for v in fcf_values if v > 0]
            if len(fcf_values) >= 2:
                # CAGR = (End/Start)^(1/n) - 1
                cagr = (fcf_values[0] / fcf_values[-1]) ** (1 / (len(fcf_values) - 1)) - 1
                # Giới hạn growth rate hợp lý: -10% đến +30%
                fcf_growth = max(-0.10, min(cagr, 0.30))
            else:
                fcf_growth = 0.05  # Mặc định 5%

        # Equity & Debt (tỷ đồng)
        equity_value = bs_data[0].get("total_equity", 0) or 0
        total_debt = (
            (bs_data[0].get("short_term_debt", 0) or 0) +
            (bs_data[0].get("long_term_debt", 0) or 0)
        )
        cash_value = bs_data[0].get("cash", 0) or 0

        # ---- Bước 2: Tính WACC ----
        cost_of_equity = self._calc_cost_of_equity(
            params['risk_free_rate'], params['beta'], params['market_return']
        )
        wacc = self._calc_wacc(
            equity_value, total_debt, cost_of_equity,
            params['cost_of_debt'], params['tax_rate']
        )

        # ---- Bước 3: Dự báo FCF ----
        projected = self._project_fcf(base_fcf, fcf_growth, params['projection_years'])

        # ---- Bước 4: Terminal Value ----
        final_fcf = projected[-1]["fcf"]
        terminal_value = self._calc_terminal_value(
            final_fcf, params['terminal_growth'], wacc
        )

        # ---- Bước 5: Chiết khấu → Enterprise Value ----
        pv_fcf = sum(
            self._discount(p["fcf"], wacc, p["year"]) for p in projected
        )
        pv_terminal = self._discount(terminal_value, wacc, params['projection_years'])
        enterprise_value = pv_fcf + pv_terminal

        # Enterprise Value → Equity Value
        # Equity Value = EV − Net Debt
        net_debt = total_debt - cash_value
        equity_val = enterprise_value - net_debt

        # Lấy số cổ phiếu lưu hành
        ratio_result = await self._data_tool.get_financial_ratio(symbol)
        shares_outstanding = 1  # fallback
        if ratio_result.get("success") and ratio_result["data"]:
            flat = {}
            for k, v in ratio_result["data"][0].items():
                if isinstance(k, tuple):
                    flat[k[1]] = v
                else:
                    flat[k] = v
            shares_raw = flat.get("Số CP lưu hành (Triệu CP)", 0) or 0
            if shares_raw > 0:
                shares_outstanding = shares_raw  # vnstock trả về số CP thô (không phải triệu)

        # Intrinsic value per share (VNĐ)
        # equity_val tỷ đồng, shares_outstanding = raw share count
        # intrinsic = equity_val * 1e9 / shares_outstanding
        intrinsic_per_share = (equity_val * 1e9 / shares_outstanding) if shares_outstanding > 0 else 0

        # Lấy giá thị trường
        price_result = await self._data_tool.get_stock_price(symbol)
        market_price = 0
        if price_result.get("success") and price_result["data"]:
            raw_close = price_result["data"][-1].get("close", 0)
            # vnstock trả giá theo đơn vị nghìn đồng (VD: 69.1 = 69,100 VNĐ)
            market_price = raw_close * 1000

        # Áp dụng margin of safety
        safe_value = intrinsic_per_share * (1 - params['margin_of_safety'])

        # Upside / Downside
        upside = ((intrinsic_per_share - market_price) / market_price) if market_price > 0 else 0

        # Khuyến nghị
        if market_price <= 0:
            recommendation = "Không có dữ liệu giá"
        elif market_price <= safe_value:
            recommendation = "MUA MẠNH - Giá thấp hơn giá trị nội tại trừ biên an toàn"
        elif market_price <= intrinsic_per_share:
            recommendation = "MUA - Giá thấp hơn giá trị nội tại"
        elif market_price <= intrinsic_per_share * 1.1:
            recommendation = "GIỮ - Giá gần bằng giá trị nội tại"
        else:
            recommendation = "THẬN TRỌNG - Giá cao hơn giá trị nội tại"

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "dcf_valuation",
            "unit": "tỷ đồng (trừ per-share = VNĐ)",
            "data": {
                # Inputs
                "assumptions": {
                    "risk_free_rate": params['risk_free_rate'],
                    "market_return": params['market_return'],
                    "beta": params['beta'],
                    "tax_rate": params['tax_rate'],
                    "cost_of_debt": params['cost_of_debt'],
                    "terminal_growth": params['terminal_growth'],
                    "projection_years": params['projection_years'],
                    "margin_of_safety": params['margin_of_safety'],
                },
                # WACC
                "cost_of_equity": round(cost_of_equity, 4),
                "wacc": wacc,
                # FCF
                "base_fcf": round(base_fcf, 2),
                "fcf_growth_rate": round(fcf_growth, 4),
                "projected_fcf": projected,
                # Valuation
                "terminal_value": round(terminal_value, 2),
                "pv_fcf": round(pv_fcf, 2),
                "pv_terminal": round(pv_terminal, 2),
                "enterprise_value": round(enterprise_value, 2),
                "net_debt": round(net_debt, 2),
                "equity_value": round(equity_val, 2),
                "shares_outstanding": round(shares_outstanding),
                # Per share
                "intrinsic_value_per_share": round(intrinsic_per_share),
                "safe_value_per_share": round(safe_value),
                "market_price": round(market_price),
                "upside": round(upside, 4),
                "recommendation": recommendation,
            },
        }

    # ===================================================================
    # 2. WACC ONLY
    # ===================================================================

    async def calculate_wacc_only(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Chỉ tính WACC."""
        params = self._get_params(**kwargs)

        bs_result = await self._fs_tool.get_balance_sheet(symbol, years=1)
        if not bs_result.get("success") or not bs_result["data"]:
            return {"success": False, "error": "Không lấy được bảng cân đối kế toán"}

        bs = bs_result["data"][0]
        equity_value = bs.get("total_equity", 0) or 0
        total_debt = (bs.get("short_term_debt", 0) or 0) + (bs.get("long_term_debt", 0) or 0)

        cost_of_equity = self._calc_cost_of_equity(
            params['risk_free_rate'], params['beta'], params['market_return']
        )
        wacc = self._calc_wacc(
            equity_value, total_debt, cost_of_equity,
            params['cost_of_debt'], params['tax_rate']
        )

        total = equity_value + total_debt
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "wacc",
            "data": {
                "equity_value": round(equity_value, 2),
                "debt_value": round(total_debt, 2),
                "weight_equity": round(equity_value / total, 4) if total > 0 else 1,
                "weight_debt": round(total_debt / total, 4) if total > 0 else 0,
                "cost_of_equity": round(cost_of_equity, 4),
                "cost_of_debt": params['cost_of_debt'],
                "tax_rate": params['tax_rate'],
                "wacc": wacc,
            },
        }

    # ===================================================================
    # 3. SENSITIVITY ANALYSIS
    # ===================================================================

    async def sensitivity_analysis(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phân tích độ nhạy: thay đổi WACC và Terminal Growth →
        xem giá trị nội tại thay đổi bao nhiêu.
        """
        # Lấy kết quả DCF gốc
        base_result = await self.run_dcf_valuation(symbol, **kwargs)
        if not base_result.get("success"):
            return base_result

        base_data = base_result["data"]
        base_wacc = base_data["wacc"]
        base_tg = base_data["assumptions"]["terminal_growth"]
        base_fcf = base_data["base_fcf"]
        fcf_growth = base_data["fcf_growth_rate"]
        years = base_data["assumptions"]["projection_years"]
        shares = base_data["shares_outstanding"]
        net_debt = base_data["net_debt"]

        # Dải WACC và Terminal Growth
        wacc_range = [
            round(base_wacc - 0.02, 4),
            round(base_wacc - 0.01, 4),
            base_wacc,
            round(base_wacc + 0.01, 4),
            round(base_wacc + 0.02, 4),
        ]
        tg_range = [
            round(base_tg - 0.01, 4),
            base_tg,
            round(base_tg + 0.01, 4),
        ]

        matrix = []
        for wacc in wacc_range:
            row = {"wacc": wacc}
            for tg in tg_range:
                # Tính lại DCF nhanh
                projected = self._project_fcf(base_fcf, fcf_growth, years)
                final_fcf = projected[-1]["fcf"]
                tv = self._calc_terminal_value(final_fcf, tg, wacc)
                pv_fcf = sum(self._discount(p["fcf"], wacc, p["year"]) for p in projected)
                pv_tv = self._discount(tv, wacc, years)
                ev = pv_fcf + pv_tv
                eq = ev - net_debt
                iv = round((eq * 1e9 / shares)) if shares > 0 else 0
                row[f"tg_{tg}"] = iv
            matrix.append(row)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "sensitivity_analysis",
            "base_case": {
                "wacc": base_wacc,
                "terminal_growth": base_tg,
                "intrinsic_value": base_data["intrinsic_value_per_share"],
            },
            "sensitivity_matrix": matrix,
            "note": "Ma trận giá trị nội tại (VNĐ/CP) theo WACC và Terminal Growth",
        }
