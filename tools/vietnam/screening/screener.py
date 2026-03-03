
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from dexter_vietnam.tools.vietnam.fundamental.ratios import FinancialRatiosTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import math
import pandas as pd
import ta
import time
import logging

logger = logging.getLogger(__name__)


class StockScreenerTool(BaseTool):

    # Danh sách blue-chip + mid-cap phổ biến để scan
    DEFAULT_UNIVERSE = [
        # Ngân hàng
        "VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "STB", "TPB",
        "SHB", "MSB", "LPB", "OCB", "EIB", "VIB", "SSB",
        # Bất động sản
        "VHM", "VIC", "NVL", "KDH", "DXG", "HDG", "NLG", "PDR", "DIG", "KBC",
        "IJC", "CEO", "SCR", "HQC",
        # Chứng khoán
        "SSI", "VND", "HCM", "VCI", "SHS", "MBS", "BSI", "CTS", "ORS",
        # Thép & vật liệu
        "HPG", "HSG", "NKG", "TLH", "VGS",
        # Thực phẩm & đồ uống
        "VNM", "MSN", "SAB", "QNS", "MCH",
        # Dầu khí
        "GAS", "PLX", "PVD", "PVS", "BSR", "OIL",
        # Công nghệ
        "FPT", "CMG", "ELC",
        # Điện
        "POW", "GEG", "PC1", "REE", "PPC", "NT2",
        # Hàng không & cảng
        "HVN", "VJC", "ACV", "GMD", "VSC",
        # Bảo hiểm
        "BVH", "BMI", "MIG", "PVI",
        # Khác
        "PNJ", "MWG", "DGW", "FRT", "HAX", "SCS", "VTP", "CTR",
        "PHR", "DPM", "DCM", "LAS", "HAG", "HNG",
    ]

    # Ánh xạ tên ngành → từ khoá (vnstock trả về tiếng Anh/Việt)
    INDUSTRY_KEYWORDS = {
        "ngan_hang": ["bank", "ngân hàng", "tài chính"],
        "bat_dong_san": ["real estate", "bất động sản", "xây dựng"],
        "chung_khoan": ["securities", "chứng khoán", "financial services"],
        "thep": ["steel", "thép", "kim loại", "metal"],
        "thuc_pham": ["food", "thực phẩm", "đồ uống", "beverage", "consumer"],
        "dau_khi": ["oil", "gas", "dầu khí", "energy", "năng lượng"],
        "cong_nghe": ["technology", "công nghệ", "software", "phần mềm", "IT"],
        "dien": ["electric", "điện", "power", "utilities", "tiện ích"],
        "hang_khong": ["airline", "hàng không", "aviation"],
        "cang_bien": ["port", "cảng", "logistics", "vận tải"],
        "bao_hiem": ["insurance", "bảo hiểm"],
        "ban_le": ["retail", "bán lẻ", "consumer"],
        "duoc_pham": ["pharma", "dược", "health", "y tế"],
        "det_may": ["textile", "dệt may", "garment"],
        "thuy_san": ["seafood", "thuỷ sản", "aquaculture"],
        "cao_su": ["rubber", "cao su"],
        "phan_bon": ["fertilizer", "phân bón", "hoá chất", "chemical"],
    }

    def __init__(self):
        self._data_tool = VnstockTool()
        self._ratio_tool = FinancialRatiosTool()

    def get_name(self) -> str:
        return "stock_screener"

    def get_description(self) -> str:
        return (
            "Sàng lọc cổ phiếu: value stocks, growth stocks, oversold/overbought, "
            "lọc theo ngành, cổ tức, bộ lọc tuỳ chỉnh."
        )

    def get_actions(self) -> dict:
        return {
            "value": "Lọc cổ phiếu giá trị: P/E thấp, ROE cao, P/B thấp",
            "growth": "Lọc cổ phiếu tăng trưởng: EPS tăng mạnh, doanh thu tăng",
            "oversold": "Lọc cổ phiếu quá bán: RSI < 30 (cơ hội mua)",
            "overbought": "Lọc cổ phiếu quá mua: RSI > 70 (cơ hội bán)",
            "industry": "Lọc cổ phiếu theo ngành (cần industry trong params)",
            "dividend": "Lọc cổ phiếu cổ tức cao và ổn định",
            "custom": "Bộ lọc tuỳ chỉnh (truyền criteria trong params)",
        }

    def get_parameters_schema(self) -> dict:
        no_param = {"properties": {}, "required": []}
        return {
            "value": no_param,
            "growth": no_param,
            "oversold": no_param,
            "overbought": no_param,
            "industry": {
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Tên ngành: ngan_hang, bat_dong_san, chung_khoan, thep, thuc_pham, dau_khi, cong_nghe, dien, hang_khong, bao_hiem, ban_le, duoc_pham",
                    }
                },
                "required": ["industry"],
            },
            "dividend": no_param,
            "custom": {
                "properties": {
                    "criteria": {
                        "type": "string",
                        "description": "Tiêu chí lọc tuỳ chỉnh (JSON string)",
                    }
                },
                "required": [],
            },
        }


    def run(self, symbol: str = "", action: str = "value", **kwargs) -> Dict[str, Any]:

        action_map = {
            "value": self._screen_value,
            "value_stocks" : self._screen_value,
            "growth_stocks": self._screen_growth,
            "growth": self._screen_growth,
            "oversold": self._screen_oversold,
            "overbought": self._screen_overbought,
            "industry": self._screen_industry,
            "dividend": self._screen_dividend,
            "custom": self._screen_custom,
        }
        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. "
                         f"Sử dụng: {list(action_map.keys())}",
            }
        try:
            return action_map[action](**kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _safe(self, val: Any) -> Optional[float]:
        """Chuyển giá trị sang float an toàn."""
        if val is None:
            return None
        try:
            v = float(val)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        except (TypeError, ValueError):
            return None

    def _r(self, val: Any, decimals: int = 2) -> Any:
        v = self._safe(val)
        return round(v, decimals) if v is not None else None

    def _flatten_ratio(self, row: Dict) -> Dict[str, Any]:
        """Flatten MultiIndex tuple-keys (từ vnstock financial ratio)."""
        flat = {}
        for key, val in row.items():
            if isinstance(key, tuple):
                flat[key[1]] = val
            else:
                flat[key] = val
        return flat

    def _convert_ratio_data(self, data: Dict) -> Dict[str, Any]:
        """Convert nested ratio data từ FinancialRatiosTool sang flat format."""
        flat = {}
        
        # Valuation ratios
        val = data.get("valuation", {})
        flat["P/E"] = val.get("pe", {}).get("value")
        flat["P/B"] = val.get("pb", {}).get("value")
        flat["P/S"] = val.get("ps", {}).get("value")
        flat["Vốn hóa (Tỷ đồng)"] = val.get("market_cap_billion", {}).get("value")
        
        # Profitability ratios
        prof = data.get("profitability", {})
        flat["ROE (%)"] = prof.get("roe", {}).get("value")
        flat["ROA (%)"] = prof.get("roa", {}).get("value")
        flat["ROIC (%)"] = prof.get("roic", {}).get("value")
        flat["Biên lợi nhuận gộp (%)"] = prof.get("gross_margin", {}).get("value")
        flat["Biên lợi nhuận ròng (%)"] = prof.get("net_margin", {}).get("value")
        flat["Biên EBIT (%)"] = prof.get("ebit_margin", {}).get("value")
        flat["Tỷ suất cổ tức (%)"] = prof.get("dividend_yield", {}).get("value")
        
        # Liquidity ratios
        liq = data.get("liquidity", {})
        flat["Chỉ số thanh toán hiện thời"] = liq.get("current_ratio", {}).get("value")
        flat["Chỉ số thanh toán nhanh"] = liq.get("quick_ratio", {}).get("value")
        flat["Chỉ số thanh toán tiền mặt"] = liq.get("cash_ratio", {}).get("value")
        
        # Leverage ratios
        lev = data.get("leverage", {})
        flat["Nợ/VCSH"] = lev.get("debt_equity", {}).get("value")
        flat["Đòn bẩy tài chính"] = lev.get("financial_leverage", {}).get("value")
        
        # Per share ratios
        ps = data.get("per_share", {})
        flat["EPS (VND)"] = ps.get("eps", {}).get("value")
        flat["BVPS (VND)"] = ps.get("bvps", {}).get("value")
        
        # Efficiency ratios
        eff = data.get("efficiency", {})
        flat["Vòng quay tài sản"] = eff.get("asset_turnover", {}).get("value")
        flat["Vòng quay TSCĐ"] = eff.get("fixed_asset_turnover", {}).get("value")
        
        # Year
        flat["Năm"] = data.get("year")
        
        return flat

    def _get_universe(self, kwargs: Dict) -> List[str]:
        """Lấy danh sách mã cần scan."""
        max_universe_size = kwargs.get("max_universe_size", 10)  # Giảm xuống 10 mã để tránh timeout
        
        if "universe" in kwargs and kwargs["universe"]:
            universe = kwargs["universe"]
        else:
            universe = self.DEFAULT_UNIVERSE.copy()
        
        # Giới hạn số lượng mã để tránh timeout
        limited_universe = universe[:max_universe_size]
        logger.info(f"🎯 Sẽ quét {len(limited_universe)} mã cổ phiếu")
        return limited_universe

    def _fetch_ratio_for_symbol(self, symbol: str, delay: float = 0.5) -> Optional[Dict[str, Any]]:
        """Lấy ratio mới nhất cho 1 mã từ FinancialRatiosTool với delay để tránh rate limit."""
        try:
            # Thêm delay nhỏ giữa các request để tránh rate limit
            if delay > 0:
                time.sleep(delay)
            
            result = self._ratio_tool.run(action="all", symbol=symbol)
            if result.get("success") and result.get("data"):
                logger.info(f"✓ Đã lấy dữ liệu tài chính cho {symbol}")
                # Convert nested structure to flat structure
                return self._convert_ratio_data(result["data"])
            else:
                logger.warning(f"✗ Không có dữ liệu tài chính cho {symbol}")
        except TimeoutError:
            logger.warning(f"⏱ Timeout khi lấy dữ liệu {symbol}")
        except Exception as e:
            logger.warning(f"✗ Lỗi lấy dữ liệu {symbol}: {str(e)[:50]}")
        return None

    def _fetch_price_df(self, symbol: str, days: int = 100, delay: float = 0.5) -> Optional[pd.DataFrame]:
        """Lấy lịch sử giá gần nhất với delay để tránh rate limit."""
        try:
            # Thêm delay nhỏ giữa các request
            if delay > 0:
                time.sleep(delay)
            
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            result = self._data_tool.get_stock_price(symbol, start=start, end=end)
            if not result.get("success"):
                logger.warning(f"✗ Không lấy được giá cho {symbol}")
                return None
            df = pd.DataFrame(result["data"])
            if df.empty:
                return None
            col_map = {"time": "date"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            logger.info(f"✓ Đã lấy lịch sử giá cho {symbol}")
            return df
        except TimeoutError:
            logger.warning(f"⏱ Timeout khi lấy giá {symbol}")
        except Exception as e:
            logger.warning(f"✗ Lỗi lấy giá {symbol}: {str(e)[:50]}")
        return None

    def _get_company_industry(self, symbol: str) -> Optional[str]:
        """Lấy ngành của cổ phiếu."""
        try:
            result = self._data_tool.get_stock_overview(symbol)
            if result.get("success"):
                data = result.get("data", {})
                # Thử nhiều key phổ biến
                for key in ["industry", "industryEn", "industryName", "icb_name3",
                            "icb_name2", "icb_name4", "sector"]:
                    val = data.get(key)
                    if val:
                        return str(val)
        except Exception:
            pass
        return None


    def _screen_value(self, **kwargs) -> Dict[str, Any]:

        criteria = kwargs.get("criteria", {})
        max_pe = criteria.get("max_pe", 15)
        max_pb = criteria.get("max_pb", 1.5)
        min_roe = criteria.get("min_roe", 0.15)
        max_de = criteria.get("max_de", 1.0)
        max_results = kwargs.get("max_results", 20)

        universe = self._get_universe(kwargs)
        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            ratio = self._fetch_ratio_for_symbol(sym)
            if ratio is None:
                errors += 1
                continue
            scanned += 1

            pe = self._safe(ratio.get("P/E"))
            pb = self._safe(ratio.get("P/B"))
            roe = self._safe(ratio.get("ROE (%)"))
            de = self._safe(ratio.get("Nợ/VCSH"))
            eps = self._safe(ratio.get("EPS (VND)"))

            # Áp dụng tiêu chí
            if pe is None or pb is None or roe is None:
                continue
            if pe <= 0:  # P/E âm = lỗ
                continue
            if pe > max_pe:
                continue
            if pb > max_pb:
                continue
            if roe < min_roe:
                continue
            if de is not None and de > max_de:
                continue
            if eps is not None and eps <= 0:
                continue

            # Tính Value Score (0-100)
            score = self._calc_value_score(pe, pb, roe, de, max_pe, max_pb, min_roe, max_de)

            matched.append({
                "symbol": sym,
                "pe": self._r(pe),
                "pb": self._r(pb),
                "roe": self._r(roe, 4),
                "de": self._r(de),
                "eps": self._r(eps, 0),
                "value_score": score,
            })

        # Sắp xếp theo value_score giảm dần
        matched.sort(key=lambda x: x["value_score"], reverse=True)
        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_value",
            "criteria": {
                "max_pe": max_pe,
                "max_pb": max_pb,
                "min_roe": f"{min_roe * 100}%",
                "max_de": max_de,
            },
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }

    def _calc_value_score(
        self, pe, pb, roe, de, max_pe, max_pb, min_roe, max_de
    ) -> int:
        """Chấm điểm value stock (0-100)."""
        score = 0

        # P/E score (0-30): càng thấp càng tốt
        if pe and pe > 0:
            pe_score = max(0, (max_pe - pe) / max_pe) * 30
            score += pe_score

        # P/B score (0-25): càng thấp càng tốt
        if pb and pb > 0:
            pb_score = max(0, (max_pb - pb) / max_pb) * 25
            score += pb_score

        # ROE score (0-25): càng cao càng tốt
        if roe:
            roe_score = min(roe / 0.30, 1.0) * 25  # cap tại 30%
            score += roe_score

        # D/E score (0-20): càng thấp càng tốt
        if de is not None and de >= 0:
            de_score = max(0, (max_de - de) / max_de) * 20
            score += de_score
        else:
            score += 10  # Không có dữ liệu → trung bình

        return min(int(score), 100)


    def _screen_growth(self, **kwargs) -> Dict[str, Any]:

        criteria = kwargs.get("criteria", {})
        min_revenue_growth = criteria.get("min_revenue_growth", 0.15)
        min_profit_growth = criteria.get("min_profit_growth", 0.15)
        min_roe = criteria.get("min_roe", 0.12)
        max_results = kwargs.get("max_results", 20)

        universe = self._get_universe(kwargs)
        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            try:
                # Lấy ratio với nhiều quý để so sánh
                result = self._ratio_tool.run(action="compare", symbol=sym, years=2)
                if not result.get("success") or not result.get("data"):
                    errors += 1
                    continue
                scanned += 1

                rows = result["data"]
                if len(rows) < 2:
                    continue

                latest = rows[0]
                previous = rows[1]

                roe = self._safe(latest.get("roe"))
                eps_now = self._safe(latest.get("eps"))
                eps_prev = self._safe(previous.get("eps"))

                # Tăng trưởng doanh thu - sử dụng gross_margin và net_margin thay vì revenue trực tiếp
                # Do FinancialRatiosTool không cung cấp revenue trực tiếp, ta ước tính từ margins
                rev_growth = None  # Sẽ bỏ qua tiêu chí này nếu không có data

                # Tăng trưởng lợi nhuận - ước tính từ net_margin changes
                margin_now = self._safe(latest.get("net_margin"))
                margin_prev = self._safe(previous.get("net_margin"))
                profit_growth = None
                if margin_now and margin_prev and margin_prev > 0:
                    profit_growth = (margin_now - margin_prev) / abs(margin_prev)

                # Tăng trưởng EPS
                eps_growth = None
                if eps_now and eps_prev and eps_prev > 0:
                    eps_growth = (eps_now - eps_prev) / abs(eps_prev)

                # Áp dụng tiêu chí (linh hoạt — chỉ cần đạt 2/3 tiêu chí growth)
                pass_count = 0
                total_criteria = 0

                if rev_growth is not None:
                    total_criteria += 1
                    if rev_growth >= min_revenue_growth:
                        pass_count += 1

                if profit_growth is not None:
                    total_criteria += 1
                    if profit_growth >= min_profit_growth:
                        pass_count += 1

                if roe is not None:
                    total_criteria += 1
                    if roe >= min_roe:
                        pass_count += 1

                if eps_now is not None:
                    total_criteria += 1
                    if eps_now > 0:
                        pass_count += 1

                # Cần đạt ≥ 2/3 tiêu chí
                if total_criteria == 0:
                    continue
                if pass_count / total_criteria < 0.66:
                    continue

                # Growth Score
                growth_score = self._calc_growth_score(
                    rev_growth, profit_growth, eps_growth, roe
                )

                matched.append({
                    "symbol": sym,
                    "revenue_growth": self._r(rev_growth * 100 if rev_growth else None, 1),
                    "profit_growth": self._r(profit_growth * 100 if profit_growth else None, 1),
                    "eps_growth": self._r(eps_growth * 100 if eps_growth else None, 1),
                    "roe": self._r(roe, 4),
                    "eps": self._r(eps_now, 0),
                    "growth_score": growth_score,
                })

            except Exception:
                errors += 1
                continue

        matched.sort(key=lambda x: x["growth_score"], reverse=True)
        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_growth",
            "criteria": {
                "min_revenue_growth": f"{min_revenue_growth * 100}%",
                "min_profit_growth": f"{min_profit_growth * 100}%",
                "min_roe": f"{min_roe * 100}%",
                "method": "Đạt ≥ 2/3 tiêu chí",
            },
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }

    def _calc_growth_score(self, rev_g, profit_g, eps_g, roe) -> int:
        """Chấm điểm growth stock (0-100)."""
        score = 0

        # Revenue growth (0-30)
        if rev_g is not None and rev_g > 0:
            score += min(rev_g / 0.50, 1.0) * 30  # cap tại 50%

        # Profit growth (0-30)
        if profit_g is not None and profit_g > 0:
            score += min(profit_g / 0.50, 1.0) * 30

        # EPS growth (0-20)
        if eps_g is not None and eps_g > 0:
            score += min(eps_g / 0.50, 1.0) * 20

        # ROE (0-20)
        if roe is not None and roe > 0:
            score += min(roe / 0.25, 1.0) * 20

        return min(int(score), 100)

    def _screen_oversold(self, **kwargs) -> Dict[str, Any]:
        """
        Lọc cổ phiếu bị bán quá mức (Oversold).
        RSI(14) < rsi_threshold (mặc định 30)
        """
        rsi_threshold = kwargs.get("rsi_threshold", 30)
        max_results = kwargs.get("max_results", 20)
        universe = self._get_universe(kwargs)

        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            df = self._fetch_price_df(sym, days=100)
            if df is None or len(df) < 20:
                errors += 1
                continue
            scanned += 1

            # Tính RSI(14)
            rsi_series = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
            rsi_val = rsi_series.iloc[-1] if not rsi_series.empty else None

            if rsi_val is None or math.isnan(rsi_val):
                continue
            if rsi_val >= rsi_threshold:
                continue

            # Thêm thông tin giá
            last_close = df["close"].iloc[-1]
            price_change_5d = None
            if len(df) >= 6:
                price_change_5d = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100

            avg_vol = df["volume"].tail(20).mean()

            matched.append({
                "symbol": sym,
                "rsi": self._r(rsi_val, 1),
                "last_close": self._r(last_close),
                "price_change_5d": self._r(price_change_5d, 1),
                "avg_volume_20d": int(avg_vol) if avg_vol else 0,
                "signal": "🟢 Oversold — Tiềm năng hồi phục",
            })

        # Sắp xếp RSI tăng dần (càng thấp càng oversold)
        matched.sort(key=lambda x: x["rsi"])
        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_oversold",
            "criteria": {"rsi_threshold": f"RSI(14) < {rsi_threshold}"},
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }


    def _screen_overbought(self, **kwargs) -> Dict[str, Any]:
        """
        Lọc cổ phiếu bị mua quá mức (Overbought).
        RSI(14) > rsi_threshold (mặc định 70)
        """
        rsi_threshold = kwargs.get("rsi_threshold", 70)
        max_results = kwargs.get("max_results", 20)
        universe = self._get_universe(kwargs)

        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            df = self._fetch_price_df(sym, days=100)
            if df is None or len(df) < 20:
                errors += 1
                continue
            scanned += 1

            rsi_series = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
            rsi_val = rsi_series.iloc[-1] if not rsi_series.empty else None

            if rsi_val is None or math.isnan(rsi_val):
                continue
            if rsi_val <= rsi_threshold:
                continue

            last_close = df["close"].iloc[-1]
            price_change_5d = None
            if len(df) >= 6:
                price_change_5d = (df["close"].iloc[-1] / df["close"].iloc[-6] - 1) * 100

            avg_vol = df["volume"].tail(20).mean()

            matched.append({
                "symbol": sym,
                "rsi": self._r(rsi_val, 1),
                "last_close": self._r(last_close),
                "price_change_5d": self._r(price_change_5d, 1),
                "avg_volume_20d": int(avg_vol) if avg_vol else 0,
                "signal": "🔴 Overbought — Cẩn thận điều chỉnh",
            })

        # Sắp xếp RSI giảm dần (càng cao càng overbought)
        matched.sort(key=lambda x: x["rsi"], reverse=True)
        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_overbought",
            "criteria": {"rsi_threshold": f"RSI(14) > {rsi_threshold}"},
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }


    def _screen_industry(self, **kwargs) -> Dict[str, Any]:

        industry = kwargs.get("industry", "")
        if not industry:
            return {
                "success": False,
                "error": "Cần cung cấp tên ngành (industry). "
                         f"Danh sách: {list(self.INDUSTRY_KEYWORDS.keys())}",
            }

        # Tìm từ khoá ngành
        industry_lower = industry.lower().replace(" ", "_")
        keywords = self.INDUSTRY_KEYWORDS.get(industry_lower)
        if not keywords:
            # Thử tìm gần đúng
            for k, v in self.INDUSTRY_KEYWORDS.items():
                if industry_lower in k or any(industry_lower in kw for kw in v):
                    keywords = v
                    industry_lower = k
                    break
        if not keywords:
            return {
                "success": False,
                "error": f"Không tìm thấy ngành '{industry}'. "
                         f"Danh sách: {list(self.INDUSTRY_KEYWORDS.keys())}",
            }

        max_results = kwargs.get("max_results", 30)
        criteria = kwargs.get("criteria", {})
        universe = self._get_universe(kwargs)

        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            scanned += 1
            sym_industry = self._get_company_industry(sym)
            if not sym_industry:
                errors += 1
                continue

            # Kiểm tra ngành
            industry_match = any(
                kw.lower() in sym_industry.lower() for kw in keywords
            )
            if not industry_match:
                continue

            # Lấy thêm ratio
            ratio = self._fetch_ratio_for_symbol(sym)
            entry = {"symbol": sym, "industry": sym_industry}

            if ratio:
                entry["pe"] = self._r(ratio.get("P/E"))
                entry["pb"] = self._r(ratio.get("P/B"))
                entry["roe"] = self._r(ratio.get("ROE (%)"), 4)
                entry["de"] = self._r(ratio.get("Nợ/VCSH"))
                entry["eps"] = self._r(ratio.get("EPS (VND)"), 0)

                # Áp dụng tiêu chí bổ sung nếu có
                if criteria:
                    if not self._check_custom_criteria(ratio, criteria):
                        continue

            matched.append(entry)

        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_industry",
            "industry": industry_lower,
            "keywords": keywords,
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }


    def _screen_dividend(self, **kwargs) -> Dict[str, Any]:

        criteria = kwargs.get("criteria", {})
        min_yield = criteria.get("min_yield", 0.05)
        max_results = kwargs.get("max_results", 20)
        universe = self._get_universe(kwargs)

        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            ratio = self._fetch_ratio_for_symbol(sym)
            if ratio is None:
                errors += 1
                continue
            scanned += 1

            div_yield = self._safe(ratio.get("Tỷ suất cổ tức (%)"))
            eps = self._safe(ratio.get("EPS (VND)"))
            pe = self._safe(ratio.get("P/E"))

            if div_yield is None:
                continue
            if div_yield < min_yield:
                continue
            if eps is not None and eps <= 0:
                continue

            matched.append({
                "symbol": sym,
                "dividend_yield": self._r(div_yield * 100 if div_yield < 1 else div_yield, 2),
                "pe": self._r(pe),
                "eps": self._r(eps, 0),
                "assessment": (
                    "🟢 Cổ tức hấp dẫn" if (div_yield if div_yield >= 1 else div_yield * 100) >= 7
                    else "🟡 Cổ tức khá"
                ),
            })

        matched.sort(key=lambda x: x["dividend_yield"] or 0, reverse=True)
        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_dividend",
            "criteria": {"min_dividend_yield": f"{min_yield * 100}%"},
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }


    def _screen_custom(self, **kwargs) -> Dict[str, Any]:

        criteria = kwargs.get("criteria", {})
        if not criteria:
            return {
                "success": False,
                "error": "Cần cung cấp criteria. Ví dụ: "
                         '{"pe": {"max": 12}, "roe": {"min": 0.15}}',
            }

        max_results = kwargs.get("max_results", 20)
        universe = self._get_universe(kwargs)

        # Tách tiêu chí RSI (cần dữ liệu giá riêng)
        rsi_criteria = criteria.pop("rsi", None)
        volume_criteria = criteria.pop("volume", None)

        matched = []
        scanned = 0
        errors = 0

        for sym in universe:
            ratio = self._fetch_ratio_for_symbol(sym)
            if ratio is None:
                errors += 1
                continue
            scanned += 1

            # Kiểm tra tiêu chí tài chính
            if not self._check_custom_criteria(ratio, criteria):
                continue

            # Kiểm tra RSI nếu có
            if rsi_criteria:
                df = self._fetch_price_df(sym, days=100)
                if df is None or len(df) < 20:
                    continue
                rsi_series = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
                rsi_val = rsi_series.iloc[-1] if not rsi_series.empty else None
                if rsi_val is None or math.isnan(rsi_val):
                    continue
                rsi_min = rsi_criteria.get("min")
                rsi_max = rsi_criteria.get("max")
                if rsi_min is not None and rsi_val < rsi_min:
                    continue
                if rsi_max is not None and rsi_val > rsi_max:
                    continue

            # Kiểm tra volume nếu có
            if volume_criteria:
                if df is None:
                    df = self._fetch_price_df(sym, days=30)
                if df is not None:
                    avg_vol = df["volume"].tail(20).mean()
                    vol_min = volume_criteria.get("min")
                    if vol_min and avg_vol < vol_min:
                        continue

            entry = {"symbol": sym}
            entry["pe"] = self._r(ratio.get("P/E"))
            entry["pb"] = self._r(ratio.get("P/B"))
            entry["roe"] = self._r(ratio.get("ROE (%)"), 4)
            entry["de"] = self._r(ratio.get("Nợ/VCSH"))
            entry["eps"] = self._r(ratio.get("EPS (VND)"), 0)
            matched.append(entry)

        matched = matched[:max_results]

        return {
            "success": True,
            "report": "screen_custom",
            "criteria": {**criteria, **({"rsi": rsi_criteria} if rsi_criteria else {}),
                         **({"volume": volume_criteria} if volume_criteria else {})},
            "scanned": scanned,
            "matched": len(matched),
            "errors": errors,
            "results": matched,
        }

    def _check_custom_criteria(self, ratio: Dict, criteria: Dict) -> bool:
        """Kiểm tra 1 mã có thoả mãn tiêu chí tuỳ chỉnh."""
        RATIO_KEY_MAP = {
            "pe": "P/E",
            "pb": "P/B",
            "roe": "ROE (%)",
            "roa": "ROA (%)",
            "de": "Nợ/VCSH",
            "eps": "EPS (VND)",
            "bvps": "BVPS (VND)",
            "gross_margin": "Biên lợi nhuận gộp (%)",
            "net_margin": "Biên lợi nhuận ròng (%)",
            "current_ratio": "Chỉ số thanh toán hiện thời",
            "quick_ratio": "Chỉ số thanh toán nhanh",
            "dividend_yield": "Tỷ suất cổ tức (%)",
        }

        for key, bounds in criteria.items():
            if not isinstance(bounds, dict):
                continue
            ratio_key = RATIO_KEY_MAP.get(key)
            if not ratio_key:
                continue
            val = self._safe(ratio.get(ratio_key))
            if val is None:
                return False
            if "min" in bounds and val < bounds["min"]:
                return False
            if "max" in bounds and val > bounds["max"]:
                return False

        return True
