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
    5. get_foreign_trading(symbol) - Giao dịch khối ngoại
    6. get_all_symbols(exchange) - Danh sách mã CP
    7. get_market_index(index_code) - Chỉ số thị trường
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
        - Giao dịch khối ngoại
        - Danh sách mã cổ phiếu theo sàn
        - Chỉ số thị trường (VNINDEX, HNX, UPCOM)
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
                - foreign_trading: Lấy giao dịch khối ngoại
                - all_symbols: Lấy danh sách mã CP
                - market_index: Lấy chỉ số thị trường
            **kwargs: Tham số cho từng action
        
        Returns:
            Dict chứa kết quả
        """
        action_map = {
            'stock_overview': self.get_stock_overview,
            'stock_price': self.get_stock_price,
            'financial_report': self.get_financial_report,
            'financial_ratio': self.get_financial_ratio,
            'foreign_trading': self.get_foreign_trading,
            'all_symbols': self.get_all_symbols,
            'market_index': self.get_market_index,
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
            # Thiết lập ngày mặc định
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
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
                
                # Convert Timestamp to string
                for record in data_records:
                    if 'time' in record and hasattr(record['time'], 'strftime'):
                        record['time'] = record['time'].strftime('%Y-%m-%d')
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "start_date": start,
                    "end_date": end,
                    "interval": interval,
                    "count": len(data_records),
                    "data": data_records
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
    
    # ===================================================================
    # 5. GET_FOREIGN_TRADING - Giao dịch khối ngoại
    # ===================================================================
    
    async def get_foreign_trading(
        self, 
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy dữ liệu giao dịch khối ngoại
        
        vnstock API: stock.trading.price_depth()
        
        Args:
            symbol: Mã cổ phiếu
            start: Ngày bắt đầu
            end: Ngày kết thúc
        
        Returns:
            {
                "success": True,
                "symbol": str,
                "data": {
                    "buy_volume": int,
                    "sell_volume": int,
                    "net_volume": int,
                    ...
                }
            }
        """
        try:
            stock = self._get_stock(symbol)
            
            # Thiết lập ngày mặc định
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Lấy dữ liệu giao dịch
            trading_data = stock.trading.price_depth(symbol=symbol.upper())
            
            if trading_data is not None:
                # Chuyển sang dict
                if isinstance(trading_data, pd.DataFrame):
                    data = trading_data.to_dict('records') if not trading_data.empty else []
                else:
                    data = trading_data if isinstance(trading_data, (dict, list)) else {}
                
                return {
                    "success": True,
                    "symbol": symbol.upper(),
                    "start_date": start,
                    "end_date": end,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": "Không có dữ liệu giao dịch khối ngoại"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy giao dịch khối ngoại {symbol}: {str(e)}"
            }
    
    # ===================================================================
    # 6. GET_ALL_SYMBOLS - Danh sách mã cổ phiếu
    # ===================================================================
    
    async def get_all_symbols(self, exchange: str = 'all') -> Dict[str, Any]:
        """
        Lấy danh sách tất cả mã cổ phiếu theo sàn
        
        vnstock API: stock.listing.all_symbols()
        
        Args:
            exchange: Sàn giao dịch
                - all: Tất cả
                - HOSE: Sàn HoSE (TP.HCM)
                - HNX: Sàn HNX (Hà Nội)
                - UPCOM: Sàn UPCOM
        
        Returns:
            {
                "success": True,
                "exchange": str,
                "count": int,
                "data": [
                    {"symbol": str, "company": str, "exchange": str},
                    ...
                ]
            }
        """
        try:
            # Lấy danh sách tất cả mã
            symbols_df = self.vnstock.stock(symbol='VNM', source='VCI').listing.all_symbols()
            
            if symbols_df is not None and not symbols_df.empty:
                # Lọc theo sàn nếu cần
                if exchange.upper() != 'ALL':
                    symbols_df = symbols_df[
                        symbols_df['exchange'].str.upper() == exchange.upper()
                    ]
                
                data_records = symbols_df.to_dict('records')
                
                return {
                    "success": True,
                    "exchange": exchange.upper(),
                    "count": len(data_records),
                    "data": data_records
                }
            else:
                return {
                    "success": False,
                    "error": "Không lấy được danh sách mã cổ phiếu"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy danh sách mã CP: {str(e)}"
            }
    
    # ===================================================================
    # 7. GET_MARKET_INDEX - Chỉ số thị trường
    # ===================================================================
    
    async def get_market_index(
        self, 
        index_code: str = 'VNINDEX',
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy dữ liệu chỉ số thị trường
        
        vnstock API: stock.quote.history() với VNINDEX/HNX/UPCOM
        
        Args:
            index_code: Mã chỉ số
                - VNINDEX: Chỉ số VN-Index (HoSE)
                - HNX: Chỉ số HNX-Index
                - UPCOM: Chỉ số UPCOM-Index
            start: Ngày bắt đầu
            end: Ngày kết thúc
        
        Returns:
            {
                "success": True,
                "index": str,
                "data": [...]
            }
        """
        try:
            # Thiết lập ngày mặc định
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Lấy dữ liệu chỉ số
            stock = self._get_stock(index_code)
            
            index_df = stock.quote.history(
                symbol=index_code.upper(),
                start=start,
                end=end,
                interval='1D'
            )
            
            if index_df is not None and not index_df.empty:
                data_records = index_df.to_dict('records')
                
                # Convert Timestamp to string
                for record in data_records:
                    if 'time' in record and hasattr(record['time'], 'strftime'):
                        record['time'] = record['time'].strftime('%Y-%m-%d')
                
                return {
                    "success": True,
                    "index": index_code.upper(),
                    "start_date": start,
                    "end_date": end,
                    "count": len(data_records),
                    "data": data_records
                }
            else:
                return {
                    "success": False,
                    "error": f"Không có dữ liệu chỉ số {index_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy chỉ số {index_code}: {str(e)}"
            }
