"""
VNStock Data Connector
Kết nối với thư viện vnstock để lấy dữ liệu chứng khoán Việt Nam
"""
from tools.base import BaseTool
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

try:
    from vnstock import Vnstock
except ImportError:
    Vnstock = None


class VNStockDataTool(BaseTool):
    """
    Tool để lấy dữ liệu cổ phiếu Việt Nam sử dụng thư viện vnstock
    
    Chức năng:
    - Lấy giá cổ phiếu hiện tại
    - Lấy lịch sử giá (OHLCV)
    - Lấy thông tin công ty
    - Lấy báo cáo tài chính
    - Lấy các chỉ số tài chính
    """
    
    def __init__(self):
        if Vnstock is None:
            raise ImportError("vnstock library is not installed. Install it with: pip install vnstock")
        self.stock = None
    
    def get_name(self) -> str:
        return "vnstock_data"
    
    def get_description(self) -> str:
        return """Lấy dữ liệu cổ phiếu Việt Nam từ vnstock. 
        Hỗ trợ: giá hiện tại, lịch sử giá, thông tin công ty, báo cáo tài chính.
        Parameters:
        - symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
        - data_type: Loại dữ liệu (quote, history, company, finance, ratios)
        - start_date: Ngày bắt đầu (format: YYYY-MM-DD) - cho history
        - end_date: Ngày kết thúc (format: YYYY-MM-DD) - cho history
        - period: Khoảng thời gian (1D, 1W, 1M) - cho history
        """
    
    async def run(
        self, 
        symbol: str,
        data_type: str = "quote",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1D",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Lấy dữ liệu cổ phiếu
        
        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
            data_type: Loại dữ liệu
                - quote: Giá hiện tại
                - history: Lịch sử giá OHLCV
                - company: Thông tin công ty
                - finance: Báo cáo tài chính
                - ratios: Các chỉ số tài chính
            start_date: Ngày bắt đầu (YYYY-MM-DD)
            end_date: Ngày kết thúc (YYYY-MM-DD)
            period: Chu kỳ dữ liệu (1D, 1W, 1M)
        
        Returns:
            Dict chứa dữ liệu được yêu cầu
        """
        try:
            # Khởi tạo Vnstock object cho symbol
            self.stock = Vnstock().stock(symbol=symbol.upper(), source='VCI')
            
            if data_type == "quote":
                return await self._get_quote(symbol)
            
            elif data_type == "history":
                return await self._get_history(symbol, start_date, end_date, period)
            
            elif data_type == "company":
                return await self._get_company_info(symbol)
            
            elif data_type == "finance":
                return await self._get_financial_report(symbol, kwargs.get('report_type', 'BalanceSheet'))
            
            elif data_type == "ratios":
                return await self._get_financial_ratios(symbol)
            
            else:
                return {
                    "success": False,
                    "error": f"Loại dữ liệu không hợp lệ: {data_type}. Sử dụng: quote, history, company, finance, ratios"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lấy dữ liệu: {str(e)}"
            }
    
    async def _get_quote(self, symbol: str) -> Dict[str, Any]:
        """Lấy giá cổ phiếu hiện tại"""
        try:
            quote_df = self.stock.quote.history(symbol=symbol, start='2024-01-01', end=datetime.now().strftime('%Y-%m-%d'))
            
            if quote_df is not None and not quote_df.empty:
                latest = quote_df.iloc[-1]
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "data": {
                        "date": str(latest.get('time', latest.name)),
                        "open": float(latest.get('open', 0)),
                        "high": float(latest.get('high', 0)),
                        "low": float(latest.get('low', 0)),
                        "close": float(latest.get('close', 0)),
                        "volume": int(latest.get('volume', 0)),
                    }
                }
            else:
                return {"success": False, "error": "Không có dữ liệu"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy giá: {str(e)}"}
    
    async def _get_history(
        self, 
        symbol: str, 
        start_date: Optional[str], 
        end_date: Optional[str],
        period: str
    ) -> Dict[str, Any]:
        """Lấy lịch sử giá OHLCV"""
        try:
            # Thiết lập ngày mặc định nếu không được cung cấp
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Lấy dữ liệu lịch sử
            history_df = self.stock.quote.history(
                symbol=symbol,
                start=start_date,
                end=end_date,
                interval=period
            )
            
            if history_df is not None and not history_df.empty:
                # Chuyển đổi DataFrame sang dict
                data_records = history_df.to_dict('records')
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "period": period,
                    "count": len(data_records),
                    "data": data_records
                }
            else:
                return {"success": False, "error": "Không có dữ liệu lịch sử"}
        
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy lịch sử: {str(e)}"}
    
    async def _get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Lấy thông tin công ty"""
        try:
            # Thử nhiều phương thức khác nhau của vnstock API
            company_info = None
            
            # Method 1: company.overview
            try:
                company_info = self.stock.company.overview()
            except:
                pass
            
            # Method 2: company.profile (older versions)
            if company_info is None:
                try:
                    company_info = self.stock.company.profile()
                except:
                    pass
            
            # Method 3: Lấy thông tin từ quote
            if company_info is None:
                try:
                    # Fallback: lấy một số thông tin cơ bản
                    company_info = {
                        "symbol": symbol.upper(),
                        "exchange": "HOSE/HNX",
                        "note": "Company info not available from vnstock API"
                    }
                except:
                    pass
            
            if company_info is not None:
                # Chuyển đổi sang dict nếu là DataFrame
                if isinstance(company_info, pd.DataFrame):
                    info_dict = company_info.to_dict('records')[0] if not company_info.empty else {}
                else:
                    info_dict = company_info
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "data": info_dict
                }
            else:
                return {"success": False, "error": "Không có thông tin công ty"}
        
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy thông tin công ty: {str(e)}"}
    
    async def _get_financial_report(self, symbol: str, report_type: str = 'BalanceSheet') -> Dict[str, Any]:
        """
        Lấy báo cáo tài chính
        report_type: BalanceSheet, IncomeStatement, CashFlow
        """
        try:
            if report_type == 'BalanceSheet':
                report = self.stock.finance.balance_sheet(period='year', lang='vi')
            elif report_type == 'IncomeStatement':
                report = self.stock.finance.income_statement(period='year', lang='vi')
            elif report_type == 'CashFlow':
                report = self.stock.finance.cash_flow(period='year', lang='vi')
            else:
                return {"success": False, "error": f"Loại báo cáo không hợp lệ: {report_type}"}
            
            if report is not None and not report.empty:
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "report_type": report_type,
                    "data": report.to_dict('records')
                }
            else:
                return {"success": False, "error": "Không có báo cáo tài chính"}
        
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy báo cáo tài chính: {str(e)}"}
    
    async def _get_financial_ratios(self, symbol: str) -> Dict[str, Any]:
        """Lấy các chỉ số tài chính"""
        try:
            ratios = self.stock.finance.ratio(period='year', lang='vi')
            
            if ratios is not None and not ratios.empty:
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "data": ratios.to_dict('records')
                }
            else:
                return {"success": False, "error": "Không có chỉ số tài chính"}
        
        except Exception as e:
            return {"success": False, "error": f"Lỗi lấy chỉ số tài chính: {str(e)}"}
