"""
Module 1: Hạ tầng Dữ liệu (P0)
VNStock Connector - Kết nối với thư viện vnstock3 để lấy dữ liệu chứng khoán Việt Nam

Theo CODING_ROADMAP.md - Module 1
"""
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd

try:
    from vnstock import Vnstock
except ImportError:
    Vnstock = None


class VnstockTool(BaseTool):
    """
    Tool chính để lấy dữ liệu từ vnstock
    
    Chức năng theo roadmap Module 1:
    1. get_stock_overview(symbol) - Thông tin công ty
    2. get_stock_price(symbol, start, end) - Lịch sử giá
    3. get_financial_report(symbol, type, period) - Báo cáo tài chính
    4. get_financial_ratio(symbol, period) - Chỉ số tài chính
    """
    
    def __init__(self):
        """Khởi tạo VnstockTool"""
        if Vnstock is None:
            raise ImportError(
                "vnstock library is not installed. "
                "Install it with: pip install vnstock"
            )
        self.vnstock = Vnstock()
        self._stock_cache = {}  # Cache cho stock objects
    
    def get_name(self) -> str:
        """Trả về tên tool"""
        return "vnstock_connector"
    
    def get_description(self) -> str:
        """Trả về mô tả tool"""
        return """VNStock Data Connector - Lấy dữ liệu chứng khoán Việt Nam.
        
        Chức năng:
        - Thông tin công ty & tổng quan
        - Lịch sử giá OHLCV
        - Báo cáo tài chính (Balance Sheet, Income Statement, Cash Flow)
        - Chỉ số tài chính (P/E, ROE, ROA, etc.)
        """
    
    async def run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Thực thi action tương ứng
        
        Args:
            action: Hành động cần thực hiện
                - stock_overview: Lấy thông tin công ty
                - stock_price: Lấy lịch sử giá
                - financial_report: Lấy báo cáo tài chính
                - financial_ratio: Lấy chỉ số tài chính
            **kwargs: Tham số cho từng action
        
        Returns:
            Dict chứa kết quả
        """
        action_map = {
            'stock_overview': self.get_stock_overview,
            'stock_price': self.get_stock_price,
            'financial_report': self.get_financial_report,
            'financial_ratio': self.get_financial_ratio,
        }
        
        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. Sử dụng: {list(action_map.keys())}"
            }
        
        try:
            return await action_map[action](**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi thực thi {action}: {str(e)}"
            }
    
    def _get_stock(self, symbol: str):
        """Helper: Lấy stock object và cache"""
        if symbol not in self._stock_cache:
            self._stock_cache[symbol] = self.vnstock.stock(
                symbol=symbol.upper(), 
                source='VCI'
            )
        return self._stock_cache[symbol]
    
    # ===================================================================
    # 1. GET_STOCK_OVERVIEW - Thông tin công ty
    # ===================================================================
    
    async def get_stock_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Lấy thông tin tổng quan về công ty
        
        vnstock API: stock.company.profile()
        
        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
        
        Returns:
            {
                "success": True,
                "symbol": str,
                "data": {
                    "companyName": str,
                    "exchange": str,
                    "industry": str,
                    ...
                }
            }
        """
        try:
            stock = self._get_stock(symbol)
            
            # Thử các phương thức khác nhau
            company_info = None
            
            # Method 1: overview
            try:
                company_info = stock.company.overview()
            except AttributeError:
                pass
            
            # Method 2: profile (older versions)
            if company_info is None:
                try:
                    company_info = stock.company.profile()
                except AttributeError:
                    pass
            
            if company_info is not None:
                # Chuyển DataFrame sang dict
                if isinstance(company_info, pd.DataFrame):
                    data = company_info.to_dict('records')[0] if not company_info.empty else {}
                else:
                    data = company_info if isinstance(company_info, dict) else {}
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "data": data
                }
            else:
                # Fallback: Trả về thông tin cơ bản
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "data": {
                        "symbol": symbol.upper(),
                        "note": "Detailed company info not available"
                    }
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy thông tin công ty {symbol}: {str(e)}"
            }
    
    # ===================================================================
    # 2. GET_STOCK_PRICE - Lịch sử giá
    # ===================================================================
    
    async def get_stock_price(
        self, 
        symbol: str, 
        start: Optional[str] = None, 
        end: Optional[str] = None,
        interval: str = '1D'
    ) -> Dict[str, Any]:
        """
        Lấy lịch sử giá OHLCV
        
        vnstock API: stock.quote.history()
        
        Args:
            symbol: Mã cổ phiếu
            start: Ngày bắt đầu (YYYY-MM-DD), mặc định 1 năm trước
            end: Ngày kết thúc (YYYY-MM-DD), mặc định hôm nay
            interval: Chu kỳ (1D, 1W, 1M)
        
        Returns:
            {
                "success": True,
                "symbol": str,
                "start_date": str,
                "end_date": str,
                "count": int,
                "data": [
                    {"time": str, "open": float, "high": float, "low": float, 
                     "close": float, "volume": int},
                    ...
                ]
            }
        """
        try:
            # Thiết lập ngày mặc định - lấy dữ liệu 30 ngày gần nhất
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            stock = self._get_stock(symbol)
            
            # Lấy dữ liệu lịch sử
            history_df = stock.quote.history(
                symbol=symbol.upper(),
                start=start,
                end=end,
                interval=interval
            )
            
            if history_df is not None and not history_df.empty:
                # Chuyển DataFrame sang list of dicts
                data_records = history_df.to_dict('records')
                
                # Convert Timestamp to string và lấy actual date range
                actual_start = None
                actual_end = None
                
                for record in data_records:
                    if 'time' in record and hasattr(record['time'], 'strftime'):
                        date_str = record['time'].strftime('%Y-%m-%d')
                        record['time'] = date_str
                        
                        # Track actual date range from data
                        if actual_start is None or date_str < actual_start:
                            actual_start = date_str
                        if actual_end is None or date_str > actual_end:
                            actual_end = date_str
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "requested_start": start,
                    "requested_end": end,
                    "actual_start": actual_start or start,
                    "actual_end": actual_end or end,
                    "interval": interval,
                    "count": len(data_records),
                    "data": data_records[:10],  # Chỉ lấy 10 records gần nhất để tiết kiệm
                    "note": f"Showing latest 10 of {len(data_records)} records. Data available from {actual_start} to {actual_end}."
                }
            else:
                return {
                    "success": False,
                    "error": "Không có dữ liệu lịch sử"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy lịch sử giá {symbol}: {str(e)}"
            }
    
    # ===================================================================
    # 3. GET_FINANCIAL_REPORT - Báo cáo tài chính
    # ===================================================================
    
    async def get_financial_report(
        self, 
        symbol: str, 
        report_type: str = 'BalanceSheet',
        period: str = 'year'
    ) -> Dict[str, Any]:
        """
        Lấy báo cáo tài chính
        
        vnstock API: 
        - stock.finance.balance_sheet()
        - stock.finance.income_statement()
        - stock.finance.cash_flow()
        
        Args:
            symbol: Mã cổ phiếu
            report_type: Loại báo cáo
                - BalanceSheet: Bảng cân đối kế toán
                - IncomeStatement: Báo cáo kết quả kinh doanh
                - CashFlow: Báo cáo lưu chuyển tiền tệ
            period: Chu kỳ (year, quarter)
        
        Returns:
            {
                "success": True,
                "symbol": str,
                "report_type": str,
                "period": str,
                "data": [...]
            }
        """
        try:
            stock = self._get_stock(symbol)
            
            # Lấy báo cáo theo loại
            if report_type == 'BalanceSheet':
                report = stock.finance.balance_sheet(period=period, lang='vi')
            elif report_type == 'IncomeStatement':
                report = stock.finance.income_statement(period=period, lang='vi')
            elif report_type == 'CashFlow':
                report = stock.finance.cash_flow(period=period, lang='vi')
            else:
                return {
                    "success": False,
                    "error": f"Loại báo cáo không hợp lệ: {report_type}. "
                            f"Sử dụng: BalanceSheet, IncomeStatement, CashFlow"
                }
            
            if report is not None and not report.empty:
                data_records = report.to_dict('records')
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "report_type": report_type,
                    "period": period,
                    "count": len(data_records),
                    "data": data_records
                }
            else:
                return {
                    "success": False,
                    "error": f"Không có báo cáo {report_type}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy báo cáo tài chính {symbol}: {str(e)}"
            }
    
    # ===================================================================
    # 4. GET_FINANCIAL_RATIO - Chỉ số tài chính
    # ===================================================================
    
    async def get_financial_ratio(
        self, 
        symbol: str, 
        period: str = 'year'
    ) -> Dict[str, Any]:
        """
        Lấy các chỉ số tài chính (P/E, ROE, ROA, etc.)
        
        vnstock API: stock.finance.ratio()
        
        Args:
            symbol: Mã cổ phiếu
            period: Chu kỳ (year, quarter)
        
        Returns:
            {
                "success": True,
                "symbol": str,
                "period": str,
                "data": [
                    {
                        "year": str,
                        "PE": float,
                        "PB": float,
                        "ROE": float,
                        "ROA": float,
                        ...
                    }
                ]
            }
        """
        try:
            stock = self._get_stock(symbol)
            
            ratios = stock.finance.ratio(period=period, lang='vi')
            
            if ratios is not None and not ratios.empty:
                data_records = ratios.to_dict('records')
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "period": period,
                    "count": len(data_records),
                    "data": data_records
                }
            else:
                return {
                    "success": False,
                    "error": "Không có dữ liệu chỉ số tài chính"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy chỉ số tài chính {symbol}: {str(e)}"
            }
