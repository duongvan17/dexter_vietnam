"""
TCBS API Connector
TODO: Kết nối với TCBS API để lấy dữ liệu chứng khoán VN
"""
from tools.base import BaseTool
from typing import Dict, Any

class TCBSTool(BaseTool):
    """
    Tool để lấy dữ liệu từ TCBS API
    
    API endpoints:
    - Giá cổ phiếu: https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/{symbol}/overview
    - Lịch sử giá: https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term
    - Thông tin công ty: https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/{symbol}/overview
    """
    
    def get_name(self) -> str:
        return "tcbs_data"
    
    def get_description(self) -> str:
        return "Lấy dữ liệu giá cổ phiếu, thông tin công ty từ TCBS"
    
    async def run(self, symbol: str = None, data_type: str = "overview", **kwargs) -> Dict[str, Any]:
        """
        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
            data_type: Loại dữ liệu (overview, price, history)
        
        TODO: Implement API calls
        """
        # TODO: Implement TCBS API integration
        pass
