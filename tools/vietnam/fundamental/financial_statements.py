
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd


class FinancialStatementsTool(BaseTool):

    BALANCE_SHEET_MAP = {
        # Tài sản
        'TÀI SẢN NGẮN HẠN (đồng)': 'current_assets',
        'Tiền và tương đương tiền (đồng)': 'cash',
        'Giá trị thuần đầu tư ngắn hạn (đồng)': 'short_term_investments',
        'Các khoản phải thu ngắn hạn (đồng)': 'short_term_receivables',
        'Hàng tồn kho ròng': 'inventory',
        'Hàng tồn kho, ròng (đồng)': 'inventory_alt',
        'Tài sản lưu động khác': 'other_current_assets',
        'TÀI SẢN DÀI HẠN (đồng)': 'non_current_assets',
        'Tài sản cố định (đồng)': 'fixed_assets',
        'Đầu tư dài hạn (đồng)': 'long_term_investments',
        'Lợi thế thương mại': 'goodwill',
        'Tài sản dài hạn khác': 'other_non_current_assets',
        'TỔNG CỘNG TÀI SẢN (đồng)': 'total_assets',
        # Nợ
        'NỢ PHẢI TRẢ (đồng)': 'total_liabilities',
        'Nợ ngắn hạn (đồng)': 'current_liabilities',
        'Nợ dài hạn (đồng)': 'non_current_liabilities',
        'Vay và nợ thuê tài chính ngắn hạn (đồng)': 'short_term_debt',
        'Vay và nợ thuê tài chính dài hạn (đồng)': 'long_term_debt',
        # Vốn chủ sở hữu
        'VỐN CHỦ SỞ HỮU (đồng)': 'total_equity',
        'Vốn góp của chủ sở hữu (đồng)': 'contributed_capital',
        'Lãi chưa phân phối (đồng)': 'retained_earnings',
        'LỢI ÍCH CỦA CỔ ĐÔNG THIỂU SỐ': 'minority_interest',
        'TỔNG CỘNG NGUỒN VỐN (đồng)': 'total_liabilities_equity',
    }

    INCOME_STATEMENT_MAP = {
        'Doanh thu (đồng)': 'revenue',
        'Doanh thu bán hàng và cung cấp dịch vụ': 'gross_revenue',
        'Các khoản giảm trừ doanh thu': 'revenue_deductions',
        'Doanh thu thuần': 'net_revenue',
        'Giá vốn hàng bán': 'cogs',
        'Lãi gộp': 'gross_profit',
        'Thu nhập tài chính': 'financial_income',
        'Chi phí tài chính': 'financial_expenses',
        'Chi phí tiền lãi vay': 'interest_expense',
        'Chi phí bán hàng': 'selling_expenses',
        'Chi phí quản lý DN': 'admin_expenses',
        'Lãi/Lỗ từ hoạt động kinh doanh': 'operating_profit',
        'Thu nhập khác': 'other_income',
        'Lợi nhuận khác': 'other_profit',
        'LN trước thuế': 'profit_before_tax',
        'Chi phí thuế TNDN hiện hành': 'current_income_tax',
        'Chi phí thuế TNDN hoãn lại': 'deferred_income_tax',
        'Lợi nhuận thuần': 'net_income',
        'Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)': 'net_income_parent',
        'Cổ đông thiểu số': 'minority_interest_income',
        'Tăng trưởng doanh thu (%)': 'revenue_growth',
        'Tăng trưởng lợi nhuận (%)': 'profit_growth',
    }

    CASH_FLOW_MAP = {
        # Hoạt động kinh doanh
        'Lãi/Lỗ ròng trước thuế': 'profit_before_tax',
        'Khấu hao TSCĐ': 'depreciation',
        'Lưu chuyển tiền thuần từ HĐKD trước thay đổi VLĐ': 'cfo_before_wc_changes',
        'Tăng/Giảm các khoản phải thu': 'change_receivables',
        'Tăng/Giảm hàng tồn kho': 'change_inventory',
        'Tăng/Giảm các khoản phải trả': 'change_payables',
        'Chi phí lãi vay đã trả': 'interest_paid',
        'Tiền thu nhập doanh nghiệp đã trả': 'income_tax_paid',
        'Lưu chuyển tiền tệ ròng từ các hoạt động SXKD': 'cfo',
        # Hoạt động đầu tư
        'Mua sắm TSCĐ': 'capex',
        'Tiền thu được từ thanh lý tài sản cố định': 'proceeds_from_asset_sales',
        'Tiền thu cổ tức và lợi nhuận được chia': 'dividends_received',
        'Lưu chuyển từ hoạt động đầu tư': 'cfi',
        # Hoạt động tài chính
        'Tiền thu được các khoản đi vay': 'borrowings_received',
        'Tiền trả các khoản đi vay': 'borrowings_repaid',
        'Cổ tức đã trả': 'dividends_paid',
        'Lưu chuyển tiền từ hoạt động tài chính': 'cff',
        # Tổng
        'Lưu chuyển tiền thuần trong kỳ': 'net_cash_change',
        'Tiền và tương đương tiền': 'cash_beginning',
        'Tiền và tương đương tiền cuối kỳ': 'cash_ending',
    }

    def __init__(self):
        self._data_tool = VnstockTool()

    def get_name(self) -> str:
        return "financial_statements"

    def get_description(self) -> str:
        return (
            "Parse và phân tích báo cáo tài chính: Balance Sheet, "
            "Income Statement, Cash Flow. Tính tăng trưởng YoY."
        )

    async def run(self, action: str = "summary", symbol: str = "", **kwargs) -> Dict[str, Any]:
        """
        Args:
            action: Hành động
                - summary: Tổng quan tài chính (mặc định)
                - balance_sheet: Bảng cân đối kế toán
                - income_statement: KQKD
                - cash_flow: Lưu chuyển tiền tệ
                - growth: Phân tích tăng trưởng YoY
            symbol: Mã cổ phiếu
            **kwargs:
                period: 'year' hoặc 'quarter' (mặc định 'year')
                years: Số năm lấy dữ liệu (mặc định 5)
        """
        action_map = {
            'summary': self.get_financial_summary,
            'balance_sheet': self.get_balance_sheet,
            'income_statement': self.get_income_statement,
            'cash_flow': self.get_cash_flow,
            'growth': self.get_growth_analysis,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        if not symbol:
            return {"success": False, "error": "Symbol không được để trống"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _normalize(self, records: List[Dict], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Chuẩn hoá tên cột Vietnamese → English keys."""
        result = []
        for row in records:
            item: Dict[str, Any] = {"symbol": row.get("CP", ""), "year": row.get("Năm", "")}
            for vn_key, en_key in mapping.items():
                if vn_key in row:
                    item[en_key] = row[vn_key]
            result.append(item)
        return result

    def _fmt(self, value: Any) -> Any:
        """Format giá trị tiền tệ thành tỷ đồng để dễ đọc."""
        if isinstance(value, (int, float)) and abs(value) > 1_000_000_000:
            return round(value / 1_000_000_000, 2)  # tỷ đồng
        return value

    def _fmt_dict(self, d: Dict[str, Any], skip: set = None) -> Dict[str, Any]:
        """Format toàn bộ dict sang tỷ đồng."""
        skip = skip or {"symbol", "year", "revenue_growth", "profit_growth"}
        return {k: (self._fmt(v) if k not in skip else v) for k, v in d.items()}

    async def _fetch(self, symbol: str, report_type: str, period: str = 'year') -> List[Dict]:
        """Gọi Module 1 để lấy raw data."""
        result = await self._data_tool.get_financial_report(
            symbol=symbol, report_type=report_type, period=period
        )
        if not result.get("success"):
            raise ValueError(result.get("error", "Không lấy được dữ liệu"))
        return result["data"]


    async def get_balance_sheet(
        self, symbol: str, period: str = 'year', years: int = 5, **_
    ) -> Dict[str, Any]:
        """
        Parse Balance Sheet → chuẩn hoá → trả về tóm tắt.

        Returns:
            {
                "success": True,
                "symbol": str,
                "unit": "tỷ đồng",
                "data": [
                    {
                        "year": 2025,
                        "total_assets": 53312.37,
                        "current_assets": 36261.18,
                        "non_current_assets": 17051.19,
                        "total_liabilities": 18829.36,
                        "total_equity": 34483.02,
                        ...
                    }
                ]
            }
        """
        raw = await self._fetch(symbol, 'BalanceSheet', period)
        normalised = self._normalize(raw, self.BALANCE_SHEET_MAP)
        # sắp xếp mới nhất trước & giới hạn số năm
        normalised.sort(key=lambda x: x.get("year", 0), reverse=True)
        normalised = normalised[:years]
        formatted = [self._fmt_dict(r) for r in normalised]
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "balance_sheet",
            "unit": "tỷ đồng",
            "count": len(formatted),
            "data": formatted,
        }


    async def get_income_statement(
        self, symbol: str, period: str = 'year', years: int = 5, **_
    ) -> Dict[str, Any]:
        """
        Parse Income Statement → chuẩn hoá.

        Returns:
            {
                "success": True,
                "data": [
                    {
                        "year": 2025,
                        "net_revenue": 63645.89,
                        "gross_profit": 26209.47,
                        "operating_profit": 11659.77,
                        "net_income": 9413.59,
                        "gross_margin": 0.4118,
                        "net_margin": 0.1479,
                        ...
                    }
                ]
            }
        """
        raw = await self._fetch(symbol, 'IncomeStatement', period)
        normalised = self._normalize(raw, self.INCOME_STATEMENT_MAP)

        # Tính thêm margins
        for item in normalised:
            nr = item.get('net_revenue', 0) or item.get('revenue', 0)
            if nr and nr != 0:
                gp = item.get('gross_profit', 0) or 0
                op = item.get('operating_profit', 0) or 0
                ni = item.get('net_income', 0) or 0
                item['gross_margin'] = round(gp / nr, 4)
                item['operating_margin'] = round(op / nr, 4)
                item['net_margin'] = round(ni / nr, 4)

        normalised.sort(key=lambda x: x.get("year", 0), reverse=True)
        normalised = normalised[:years]
        formatted = [self._fmt_dict(r, skip={
            "symbol", "year", "revenue_growth", "profit_growth",
            "gross_margin", "operating_margin", "net_margin",
        }) for r in normalised]
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "income_statement",
            "unit": "tỷ đồng",
            "count": len(formatted),
            "data": formatted,
        }


    async def get_cash_flow(
        self, symbol: str, period: str = 'year', years: int = 5, **_
    ) -> Dict[str, Any]:
        """
        Parse Cash Flow Statement → chuẩn hoá.

        Returns:
            {
                "success": True,
                "data": [
                    {
                        "year": 2025,
                        "cfo": 8668.14,   # Dòng tiền từ hoạt động KD
                        "cfi": 1976.10,   # Dòng tiền từ đầu tư
                        "cff": -11081.93, # Dòng tiền từ tài chính
                        "capex": -1762.01,
                        "free_cash_flow": 6906.13,
                        ...
                    }
                ]
            }
        """
        raw = await self._fetch(symbol, 'CashFlow', period)
        normalised = self._normalize(raw, self.CASH_FLOW_MAP)

        # Tính Free Cash Flow = CFO + CapEx (CapEx đã là số âm)
        for item in normalised:
            cfo = item.get('cfo', 0) or 0
            capex = item.get('capex', 0) or 0
            item['free_cash_flow'] = cfo + capex

        normalised.sort(key=lambda x: x.get("year", 0), reverse=True)
        normalised = normalised[:years]
        formatted = [self._fmt_dict(r) for r in normalised]
        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "cash_flow",
            "unit": "tỷ đồng",
            "count": len(formatted),
            "data": formatted,
        }


    async def get_financial_summary(
        self, symbol: str, period: str = 'year', years: int = 3, **_
    ) -> Dict[str, Any]:
        """
        Tổng hợp 3 báo cáo → trả về tóm tắt sức khoẻ tài chính.
        """
        bs = await self.get_balance_sheet(symbol, period, years)
        inc = await self.get_income_statement(symbol, period, years)
        cf = await self.get_cash_flow(symbol, period, years)

        if not all([bs.get("success"), inc.get("success"), cf.get("success")]):
            return {"success": False, "error": "Không lấy đủ dữ liệu tài chính"}

        latest_bs = bs["data"][0] if bs["data"] else {}
        latest_inc = inc["data"][0] if inc["data"] else {}
        latest_cf = cf["data"][0] if cf["data"] else {}

        summary = {
            "year": latest_bs.get("year"),
            # Balance Sheet highlights
            "total_assets": latest_bs.get("total_assets"),
            "total_liabilities": latest_bs.get("total_liabilities"),
            "total_equity": latest_bs.get("total_equity"),
            "cash": latest_bs.get("cash"),
            "inventory": latest_bs.get("inventory"),
            "short_term_debt": latest_bs.get("short_term_debt"),
            "long_term_debt": latest_bs.get("long_term_debt"),
            # Income Statement highlights
            "net_revenue": latest_inc.get("net_revenue"),
            "gross_profit": latest_inc.get("gross_profit"),
            "operating_profit": latest_inc.get("operating_profit"),
            "net_income": latest_inc.get("net_income"),
            "gross_margin": latest_inc.get("gross_margin"),
            "operating_margin": latest_inc.get("operating_margin"),
            "net_margin": latest_inc.get("net_margin"),
            "revenue_growth": latest_inc.get("revenue_growth"),
            "profit_growth": latest_inc.get("profit_growth"),
            # Cash Flow highlights
            "cfo": latest_cf.get("cfo"),
            "capex": latest_cf.get("capex"),
            "free_cash_flow": latest_cf.get("free_cash_flow"),
            "dividends_paid": latest_cf.get("dividends_paid"),
        }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "financial_summary",
            "unit": "tỷ đồng",
            "data": summary,
            "detail": {
                "balance_sheet": bs["data"],
                "income_statement": inc["data"],
                "cash_flow": cf["data"],
            },
        }


    async def get_growth_analysis(
        self, symbol: str, period: str = 'year', years: int = 5, **_
    ) -> Dict[str, Any]:
        """
        Phân tích tăng trưởng YoY cho doanh thu, lợi nhuận, tài sản, vốn chủ.
        """
        bs = await self.get_balance_sheet(symbol, period, years + 1)
        inc = await self.get_income_statement(symbol, period, years + 1)

        if not bs.get("success") or not inc.get("success"):
            return {"success": False, "error": "Không lấy đủ dữ liệu"}

        def calc_yoy(data: List[Dict], key: str) -> List[Dict]:
            """Tính tăng trưởng YoY cho một chỉ số."""
            # data đã sắp xếp mới nhất trước
            results = []
            for i in range(len(data) - 1):
                curr = data[i].get(key, 0) or 0
                prev = data[i + 1].get(key, 0) or 0
                growth = round((curr - prev) / abs(prev), 4) if prev != 0 else None
                results.append({
                    "year": data[i].get("year"),
                    "value": curr,
                    "prev_value": prev,
                    "yoy_growth": growth,
                })
            return results

        growth_data = {
            "revenue": calc_yoy(inc["data"], "net_revenue"),
            "gross_profit": calc_yoy(inc["data"], "gross_profit"),
            "operating_profit": calc_yoy(inc["data"], "operating_profit"),
            "net_income": calc_yoy(inc["data"], "net_income"),
            "total_assets": calc_yoy(bs["data"], "total_assets"),
            "total_equity": calc_yoy(bs["data"], "total_equity"),
        }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "growth_analysis",
            "unit": "tỷ đồng",
            "data": growth_data,
        }
