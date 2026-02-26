
from dexter_vietnam.tools.base import BaseTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd

try:
    from vnstock import Vnstock
except ImportError:
    Vnstock = None


class VnstockTool(BaseTool):

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

        return """VNStock Data Connector - Lấy dữ liệu chứng khoán Việt Nam.
        
        Chức năng:
        - Thông tin công ty & tổng quan
        - Lịch sử giá OHLCV
        - Báo cáo tài chính (Balance Sheet, Income Statement, Cash Flow)
        - Chỉ số tài chính (P/E, ROE, ROA, etc.)
        - Chỉ số thị trường (VNINDEX, VN30, HNX)
        """

    def get_actions(self) -> dict:
        return {
            "stock_overview": "Thông tin tổng quan công ty (tên, ngành, vốn hóa)",
            "stock_price": "Lịch sử giá OHLCV theo ngày/tuần/tháng",
            "financial_report": "Báo cáo tài chính (BalanceSheet / IncomeStatement / CashFlow)",
            "financial_ratio": "Chỉ số tài chính thô (P/E, ROE, ROA, EPS...)",
            "foreign_trading": "Giao dịch khối ngoại của 1 mã",
            "market_index": "Dữ liệu chỉ số thị trường (VNINDEX, VN30, HNX, UPCOM)",
        }

    
    async def run(self, action: str, **kwargs) -> Dict[str, Any]:

        action_map = {
            'stock_overview': self.get_stock_overview,
            'stock_price': self.get_stock_price,
            'financial_report': self.get_financial_report,
            'financial_ratio': self.get_financial_ratio,
            'foreign_trading': self.get_foreign_trading,
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

    async def get_stock_overview(self, symbol: str) -> Dict[str, Any]:

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

    
    async def get_stock_price(
        self, 
        symbol: str, 
        start: Optional[str] = None, 
        end: Optional[str] = None,
        interval: str = '1D'
    ) -> Dict[str, Any]:

        try:
            # Thiết lập ngày mặc định - lấy dữ liệu 1 năm gần nhất (đủ cho SMA 200)
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                # Lấy 365 ngày (~1 năm) để đủ tính SMA 200
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
                    "data": data_records,  # Trả về tất cả dữ liệu cho indicators
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
    

    async def get_financial_report(
        self, 
        symbol: str, 
        report_type: str = 'BalanceSheet',
        period: str = 'year'
    ) -> Dict[str, Any]:

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
    
    async def get_financial_ratio(
        self, 
        symbol: str, 
        period: str = 'quarter'
    ) -> Dict[str, Any]:

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
    
    async def get_foreign_trading(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy dữ liệu giao dịch khối ngoại."""
        try:
            stock = self._get_stock(symbol)
            
            # Thiết lập ngày mặc định
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Thử lấy dữ liệu foreign trading
            foreign_data = None
            
            # Method 1: foreign_trading
            try:
                foreign_data = stock.trading.foreign_trading(
                    symbol=symbol.upper(),
                    start_date=start,
                    end_date=end
                )
            except (AttributeError, Exception):
                pass
            
            # Method 2: price_depth với foreign info
            if foreign_data is None:
                try:
                    foreign_data = stock.trading.price_depth(symbol=symbol.upper())
                except (AttributeError, Exception):
                    pass
            
            if foreign_data is not None:
                if isinstance(foreign_data, pd.DataFrame) and not foreign_data.empty:
                    data_records = foreign_data.to_dict('records')
                    
                    # Convert timestamps
                    for record in data_records:
                        for key, val in record.items():
                            if hasattr(val, 'strftime'):
                                record[key] = val.strftime('%Y-%m-%d')
                    
                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "start": start,
                        "end": end,
                        "count": len(data_records),
                        "data": data_records
                    }
                elif isinstance(foreign_data, dict):
                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "data": foreign_data
                    }
            
            # Fallback: return empty but successful
            return {
                "success": True,
                "symbol": symbol.upper(),
                "data": [],
                "note": "Dữ liệu khối ngoại không khả dụng qua vnstock API. Có thể cần nguồn khác."
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy giao dịch khối ngoại {symbol}: {str(e)}"
            }
    
    async def get_market_index(
        self,
        index_code: str = "VNINDEX",
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = '1D'
    ) -> Dict[str, Any]:
        """Lấy dữ liệu chỉ số thị trường (VNINDEX, VN30, HNX, etc.)."""
        try:
            # Thiết lập ngày mặc định
            if end is None:
                end = datetime.now().strftime('%Y-%m-%d')
            if start is None:
                start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            stock = self._get_stock("VNM")  # Dummy stock để access trading API
            
            # Lấy dữ liệu chỉ số
            try:
                index_df = stock.quote.history(
                    symbol=index_code,
                    start=start,
                    end=end,
                    interval=interval
                )
            except Exception:
                # Fallback: thử với vnstock trực tiếp
                index_df = self.vnstock.stock(
                    symbol=index_code,
                    source='VCI'
                ).quote.history(
                    symbol=index_code,
                    start=start,
                    end=end,
                    interval=interval
                )
            
            if index_df is not None and not index_df.empty:
                data_records = index_df.to_dict('records')
                
                # Convert Timestamp to string
                actual_start = None
                actual_end = None
                
                for record in data_records:
                    if 'time' in record and hasattr(record['time'], 'strftime'):
                        date_str = record['time'].strftime('%Y-%m-%d')
                        record['time'] = date_str
                        
                        if actual_start is None or date_str < actual_start:
                            actual_start = date_str
                        if actual_end is None or date_str > actual_end:
                            actual_end = date_str
                
                return {
                    "success": True,
                    "index": index_code,
                    "requested_start": start,
                    "requested_end": end,
                    "actual_start": actual_start or start,
                    "actual_end": actual_end or end,
                    "interval": interval,
                    "count": len(data_records),
                    "data": data_records,
                }
            else:
                return {
                    "success": False,
                    "error": f"Không có dữ liệu cho chỉ số {index_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi lấy dữ liệu chỉ số {index_code}: {str(e)}"
            }
