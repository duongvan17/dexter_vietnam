
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import math
import pandas as pd

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


class MarketOverviewTool(BaseTool):

    # Đại diện mỗi ngành → để tính hiệu suất sector
    SECTOR_REPRESENTATIVES = {
        "Ngân hàng": ["VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "STB", "TPB"],
        "Bất động sản": ["VHM", "VIC", "NVL", "KDH", "DXG", "NLG", "KBC", "DIG", "PDR"],
        "Chứng khoán": ["SSI", "VND", "HCM", "VCI", "SHS", "MBS"],
        "Thép": ["HPG", "HSG", "NKG", "TLH"],
        "Thực phẩm": ["VNM", "MSN", "SAB", "QNS", "MCH"],
        "Dầu khí": ["GAS", "PLX", "PVD", "PVS", "BSR"],
        "Công nghệ": ["FPT", "CMG"],
        "Điện": ["POW", "PC1", "REE", "NT2", "GEG"],
        "Hàng không & Cảng": ["VJC", "HVN", "ACV", "GMD"],
        "Bảo hiểm": ["BVH", "BMI", "MIG", "PVI"],
        "Bán lẻ": ["MWG", "DGW", "FRT", "PNJ"],
        "Phân bón & Hoá chất": ["DPM", "DCM", "LAS"],
    }

    # Top mã vốn hoá lớn nhất (dùng để scan top gainers/losers)
    TOP_SYMBOLS = [
        "VCB", "BID", "CTG", "TCB", "MBB", "VPB", "ACB", "HDB", "STB", "TPB",
        "VHM", "VIC", "NVL", "KDH", "DXG",
        "SSI", "VND", "HCM",
        "HPG", "HSG",
        "VNM", "MSN", "SAB",
        "GAS", "PLX", "PVD", "PVS",
        "FPT", "CMG",
        "POW", "REE",
        "VJC", "HVN", "ACV", "GMD",
        "BVH",
        "MWG", "PNJ", "DGW", "FRT",
        "DPM", "DCM",
        "SHB", "LPB", "OCB", "VIB",
        "NLG", "KBC", "DIG", "PDR",
        "SHS", "MBS",
        "BSR",
        "PC1", "GEG", "NT2",
        "HAX", "SCS", "VTP", "CTR", "PHR",
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def __init__(self):
        self._data_tool = VnstockTool()

    def get_name(self) -> str:
        return "market_overview"

    def get_description(self) -> str:
        return (
            "Tổng quan thị trường: VNINDEX/HNX/UPCOM, top tăng/giảm, "
            "hiệu suất ngành, chỉ số vĩ mô, breadth."
        )

    def get_actions(self) -> dict:
        return {
            "summary": "Tổng quan đầy đủ: index + breadth + sector ranking (dùng khi hỏi về thị trường)",
            "status": "Trạng thái thị trường: index, top gainers/losers, breadth nhanh",
            "index": "Chi tiết 1 chỉ số (VNINDEX/HNX/UPCOM): trend, SMA, volatility",
            "sector": "Hiệu suất từng ngành: ngân hàng, BĐS, thép, thực phẩm...",
            "breadth": "Độ rộng thị trường: tỷ lệ CP tăng/giảm, volume phân phối",
            "macro": "Chỉ số vĩ mô: lãi suất, tỷ giá USD/VND, giá vàng SJC, GDP/CPI",
        }

    def get_parameters_schema(self) -> dict:
        no_param = {"properties": {}, "required": []}
        return {
            "summary": no_param,
            "status": no_param,
            "index": {
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Mã chỉ số: VNINDEX, VN30, HNX, UPCOM (mặc định VNINDEX)",
                    }
                },
                "required": [],
            },
            "sector": no_param,
            "breadth": no_param,
            "macro": no_param,
        }


    def run(self, symbol: str = "", action: str = "status", **kwargs) -> Dict[str, Any]:
 
        action_map = {
            "status": self._market_status,
            "index": self._index_detail,
            "sector": self._sector_performance,
            "macro": self._macro_indicators,
            "breadth": self._market_breadth,
            "summary": self._market_summary,
        }
        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. "
                         f"Sử dụng: {list(action_map.keys())}",
            }
        try:
            return action_map[action](symbol=symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _r(self, val: Any, decimals: int = 2) -> Any:
        if val is None:
            return None
        try:
            v = float(val)
            if math.isnan(v) or math.isinf(v):
                return None
            return round(v, decimals)
        except (TypeError, ValueError):
            return val

    def _get_index_snapshot(self, index_code: str, days: int = 5) -> Dict[str, Any]:
        """Lấy snapshot nhanh cho 1 chỉ số."""
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=max(days, 10))).strftime("%Y-%m-%d")

        result = self._data_tool.get_market_index(index_code, start=start, end=end)
        if not result.get("success") or not result.get("data"):
            return {"index": index_code, "error": "Không lấy được dữ liệu"}

        df = pd.DataFrame(result["data"])
        if df.empty:
            return {"index": index_code, "error": "Dữ liệu rỗng"}

        col_map = {"time": "date"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last

        close = float(last["close"])
        prev_close = float(prev["close"])
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0

        # Xu hướng 5 phiên
        if len(df) >= 6:
            close_5d_ago = float(df.iloc[-6]["close"])
            change_5d = (close - close_5d_ago) / close_5d_ago * 100
        else:
            change_5d = None

        volume = float(last.get("volume", 0))

        return {
            "index": index_code,
            "close": self._r(close),
            "change": self._r(change),
            "change_pct": self._r(change_pct),
            "change_5d_pct": self._r(change_5d),
            "high": self._r(float(last.get("high", close))),
            "low": self._r(float(last.get("low", close))),
            "volume": int(volume),
            "date": last["date"].strftime("%Y-%m-%d") if hasattr(last["date"], "strftime") else str(last["date"]),
            "trend": "🟢 Tăng" if change > 0 else ("🔴 Giảm" if change < 0 else "⚪ Đi ngang"),
        }

    def _get_stock_change(self, symbol: str, days: int = 5) -> Optional[Dict[str, Any]]:
        """Lấy thay đổi giá 1 mã."""
        try:
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=max(days + 5, 15))).strftime("%Y-%m-%d")

            result = self._data_tool.get_stock_price(symbol, start=start, end=end)
            if not result.get("success") or not result.get("data"):
                return None

            df = pd.DataFrame(result["data"])
            if df.empty or len(df) < 2:
                return None

            col_map = {"time": "date"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            last = df.iloc[-1]
            prev = df.iloc[-2]

            close = float(last["close"])
            prev_close = float(prev["close"])
            change_pct = (close - prev_close) / prev_close * 100 if prev_close != 0 else 0
            volume = float(last.get("volume", 0))

            # Change over N days
            change_nd = None
            if len(df) >= days + 1:
                old_close = float(df.iloc[-(days + 1)]["close"])
                change_nd = (close - old_close) / old_close * 100 if old_close != 0 else 0

            return {
                "symbol": symbol,
                "close": self._r(close),
                "change_1d_pct": self._r(change_pct),
                "change_nd_pct": self._r(change_nd),
                "volume": int(volume),
            }
        except Exception:
            return None


    def _market_status(self, **kwargs) -> Dict[str, Any]:

        top_n = kwargs.get("top_n", 10)

        # Lấy 3 chỉ số chính
        indices = {}
        for idx in ["VNINDEX", "HNX", "UPCOM"]:
            indices[idx] = self._get_index_snapshot(idx)

        # Scan top gainers / losers
        stock_changes = []
        for sym in self.TOP_SYMBOLS:
            info = self._get_stock_change(sym, days=1)
            if info:
                stock_changes.append(info)

        # Sắp xếp
        gainers = sorted(
            [s for s in stock_changes if s["change_1d_pct"] is not None],
            key=lambda x: x["change_1d_pct"],
            reverse=True,
        )[:top_n]

        losers = sorted(
            [s for s in stock_changes if s["change_1d_pct"] is not None],
            key=lambda x: x["change_1d_pct"],
        )[:top_n]

        # Thống kê breadth nhanh
        up = sum(1 for s in stock_changes if s.get("change_1d_pct", 0) > 0)
        down = sum(1 for s in stock_changes if s.get("change_1d_pct", 0) < 0)
        flat = len(stock_changes) - up - down

        # Đánh giá chung
        vni = indices.get("VNINDEX", {})
        vni_change = vni.get("change_pct", 0) or 0
        if vni_change > 1:
            sentiment = "🟢 TÍCH CỰC — Thị trường tăng mạnh"
        elif vni_change > 0:
            sentiment = "🟢 TÍCH CỰC NHẸ — Thị trường tăng nhẹ"
        elif vni_change > -1:
            sentiment = "🟡 TRUNG LẬP — Thị trường giảm nhẹ / đi ngang"
        else:
            sentiment = "🔴 TIÊU CỰC — Thị trường giảm mạnh"

        return {
            "success": True,
            "report": "market_status",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sentiment": sentiment,
            "indices": indices,
            "breadth_quick": {
                "up": up,
                "down": down,
                "flat": flat,
                "scanned": len(stock_changes),
            },
            "top_gainers": gainers,
            "top_losers": losers,
        }


    def _index_detail(self, **kwargs) -> Dict[str, Any]:

        index_code = kwargs.get("symbol", "VNINDEX").upper()
        if index_code not in ["VNINDEX", "HNX", "UPCOM"]:
            index_code = "VNINDEX"

        period = kwargs.get("period", "3m")
        period_days = {"1d": 5, "5d": 10, "1m": 35, "3m": 100, "6m": 200, "1y": 370}
        days = period_days.get(period, 100)

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = self._data_tool.get_market_index(index_code, start=start, end=end)
        if not result.get("success") or not result.get("data"):
            return {"success": False, "error": f"Không có dữ liệu {index_code}"}

        df = pd.DataFrame(result["data"])
        col_map = {"time": "date"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        last = df.iloc[-1]
        first = df.iloc[0]

        close = float(last["close"])
        open_period = float(first["close"])
        period_change = (close - open_period) / open_period * 100 if open_period != 0 else 0

        # Thống kê
        high_period = float(df["high"].max())
        low_period = float(df["low"].min())

        # SMA
        sma20 = float(df["close"].tail(20).mean()) if len(df) >= 20 else None
        sma50 = float(df["close"].tail(50).mean()) if len(df) >= 50 else None

        # Volatility
        df["daily_return"] = df["close"].pct_change()
        daily_vol = df["daily_return"].std()
        annual_vol = daily_vol * (252 ** 0.5) if daily_vol else None

        # Trend
        if sma20 and sma50:
            if close > sma20 > sma50:
                trend = "🟢 Uptrend (Giá > SMA20 > SMA50)"
            elif close < sma20 < sma50:
                trend = "🔴 Downtrend (Giá < SMA20 < SMA50)"
            elif close > sma20:
                trend = "🟡 Hồi phục (Giá > SMA20)"
            else:
                trend = "🟡 Điều chỉnh (Giá < SMA20)"
        elif sma20:
            trend = "🟢 Trên SMA20" if close > sma20 else "🔴 Dưới SMA20"
        else:
            trend = "N/A"

        return {
            "success": True,
            "report": "index_detail",
            "index": index_code,
            "period": period,
            "current": {
                "close": self._r(close),
                "date": last["date"].strftime("%Y-%m-%d") if hasattr(last["date"], "strftime") else str(last["date"]),
            },
            "period_stats": {
                "change_pct": self._r(period_change),
                "high": self._r(high_period),
                "low": self._r(low_period),
                "trading_days": len(df),
            },
            "technicals": {
                "sma20": self._r(sma20),
                "sma50": self._r(sma50),
                "volatility_annual_pct": self._r(annual_vol * 100 if annual_vol else None),
                "trend": trend,
            },
        }


    def _sector_performance(self, **kwargs) -> Dict[str, Any]:

        period = kwargs.get("period", "1d")
        period_days = {"1d": 5, "5d": 10, "1m": 35, "3m": 100}
        days = period_days.get(period, 5)

        sectors = {}

        for sector_name, symbols in self.SECTOR_REPRESENTATIVES.items():
            changes = []
            for sym in symbols:
                info = self._get_stock_change(sym, days=days)
                if info:
                    # Dùng change_1d cho period 1d, change_nd cho period dài hơn
                    change = info.get("change_nd_pct") if period != "1d" else info.get("change_1d_pct")
                    if change is not None:
                        changes.append({"symbol": sym, "change_pct": change, "close": info["close"]})

            if changes:
                avg_change = sum(c["change_pct"] for c in changes) / len(changes)
                best = max(changes, key=lambda x: x["change_pct"])
                worst = min(changes, key=lambda x: x["change_pct"])
            else:
                avg_change = None
                best = None
                worst = None

            sectors[sector_name] = {
                "avg_change_pct": self._r(avg_change),
                "stocks_tracked": len(changes),
                "best": best,
                "worst": worst,
            }

        # Xếp hạng ngành
        ranked = sorted(
            [(name, data) for name, data in sectors.items() if data["avg_change_pct"] is not None],
            key=lambda x: x[1]["avg_change_pct"],
            reverse=True,
        )

        ranking = []
        for i, (name, data) in enumerate(ranked, 1):
            avg = data["avg_change_pct"]
            if avg > 1:
                signal = "🟢 Mạnh"
            elif avg > 0:
                signal = "🟢 Tích cực"
            elif avg > -1:
                signal = "🟡 Đi ngang"
            else:
                signal = "🔴 Yếu"

            ranking.append({
                "rank": i,
                "sector": name,
                "avg_change_pct": avg,
                "signal": signal,
                "stocks_tracked": data["stocks_tracked"],
                "best_stock": data["best"],
                "worst_stock": data["worst"],
            })

        return {
            "success": True,
            "report": "sector_performance",
            "period": period,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sectors": ranking,
            "top_sectors": [r["sector"] for r in ranking[:3]],
            "bottom_sectors": [r["sector"] for r in ranking[-3:]],
        }


    def _macro_indicators(self, **kwargs) -> Dict[str, Any]:
 
        macro = {}

        # --- Lãi suất ---
        macro["interest_rates"] = {
            "refinancing_rate": "4.5%",
            "rediscount_rate": "3.0%",
            "overnight_rate": "0.1%",
            "deposit_ceiling_lt6m": "4.75%",
            "note": "Lãi suất điều hành SBV (cập nhật định kỳ). "
                    "Giá trị tham khảo — kiểm tra SBV.gov.vn để có số mới nhất.",
            "source": "SBV",
        }

        # --- Tỷ giá & Vàng (thử crawl) ---
        fx_gold = self._fetch_fx_gold()
        macro["exchange_rate"] = fx_gold.get("exchange_rate", {"note": "Không lấy được"})
        macro["gold_price"] = fx_gold.get("gold_price", {"note": "Không lấy được"})

        # --- VNINDEX context ---
        vni = self._get_index_snapshot("VNINDEX", days=30)
        macro["vnindex"] = {
            "close": vni.get("close"),
            "change_pct": vni.get("change_pct"),
            "trend": vni.get("trend"),
        }

        # --- GDP & CPI ---
        macro["gdp"] = {
            "latest": "~6.5%",
            "note": "GDP Việt Nam (ước tính). Nguồn: GSO.gov.vn",
        }
        macro["cpi"] = {
            "latest": "~3.5%",
            "note": "CPI YoY (ước tính). Nguồn: GSO.gov.vn",
        }

        # --- Đánh giá ---
        assessment = []
        if vni.get("change_pct") is not None:
            if vni["change_pct"] > 0:
                assessment.append("🟢 VNINDEX tăng — tâm lý tích cực")
            else:
                assessment.append("🔴 VNINDEX giảm — cẩn thận")

        macro["assessment"] = assessment

        return {
            "success": True,
            "report": "macro_indicators",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data": macro,
            "disclaimer": "Một số chỉ số vĩ mô là ước tính / cập nhật định kỳ. "
                          "Vui lòng kiểm tra nguồn chính thức (SBV, GSO, NHNN).",
        }

    def _fetch_fx_gold(self) -> Dict[str, Any]:
        """Thử crawl tỷ giá và giá vàng."""
        result = {}
        if requests is None or BeautifulSoup is None:
            return result

        # Tỷ giá USD/VND từ VCB
        try:
            url = "https://portal.vietcombank.com.vn/Usercontrols/TV498/ExchangeSt498.aspx"
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Tìm USD row
                rows = soup.find_all("tr")
                for row in rows:
                    tds = row.find_all("td")
                    if tds and "USD" in tds[0].get_text():
                        buy = tds[1].get_text(strip=True) if len(tds) > 1 else None
                        sell = tds[2].get_text(strip=True) if len(tds) > 2 else None
                        result["exchange_rate"] = {
                            "USD_VND_buy": buy,
                            "USD_VND_sell": sell,
                            "source": "Vietcombank",
                        }
                        break
        except Exception:
            pass

        # Giá vàng SJC
        try:
            url = "https://sjc.com.vn/xml/tygiavang.xml"
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                items = soup.find_all("ratelist") or soup.find_all("item")
                if items:
                    first = items[0]
                    buy = first.get("buy") or first.find("buy")
                    sell = first.get("sell") or first.find("sell")
                    result["gold_price"] = {
                        "buy": str(buy) if buy else None,
                        "sell": str(sell) if sell else None,
                        "unit": "triệu VND/lượng",
                        "source": "SJC",
                    }
        except Exception:
            pass

        return result


    def _market_breadth(self, **kwargs) -> Dict[str, Any]:
 
        universe = self.TOP_SYMBOLS
        stocks = []

        for sym in universe:
            info = self._get_stock_change(sym, days=1)
            if info:
                stocks.append(info)

        if not stocks:
            return {"success": False, "error": "Không lấy được dữ liệu"}

        up = [s for s in stocks if (s.get("change_1d_pct") or 0) > 0]
        down = [s for s in stocks if (s.get("change_1d_pct") or 0) < 0]
        flat = [s for s in stocks if (s.get("change_1d_pct") or 0) == 0]

        total_vol = sum(s.get("volume", 0) for s in stocks)
        vol_up = sum(s.get("volume", 0) for s in up)
        vol_down = sum(s.get("volume", 0) for s in down)

        ad_ratio = len(up) / len(down) if len(down) > 0 else float("inf")
        vol_ratio = vol_up / vol_down if vol_down > 0 else float("inf")

        # Đánh giá
        if ad_ratio > 2:
            breadth_signal = "🟢 Rất mạnh — Đa số CP tăng"
        elif ad_ratio > 1.2:
            breadth_signal = "🟢 Tích cực — Nhiều CP tăng hơn giảm"
        elif ad_ratio > 0.8:
            breadth_signal = "🟡 Trung lập — Cân bằng tăng/giảm"
        elif ad_ratio > 0.5:
            breadth_signal = "🟠 Yếu — Nhiều CP giảm"
        else:
            breadth_signal = "🔴 Rất yếu — Đa số CP giảm"

        return {
            "success": True,
            "report": "market_breadth",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stocks_scanned": len(stocks),
            "advance_decline": {
                "advancing": len(up),
                "declining": len(down),
                "unchanged": len(flat),
                "ad_ratio": self._r(ad_ratio) if ad_ratio != float("inf") else "∞",
            },
            "volume_distribution": {
                "total": int(total_vol),
                "up_volume": int(vol_up),
                "down_volume": int(vol_down),
                "up_volume_pct": self._r(vol_up / total_vol * 100 if total_vol > 0 else 0),
                "vol_ratio": self._r(vol_ratio) if vol_ratio != float("inf") else "∞",
            },
            "signal": breadth_signal,
            "top_volume": sorted(stocks, key=lambda x: x.get("volume", 0), reverse=True)[:5],
        }


    def _market_summary(self, **kwargs) -> Dict[str, Any]:

        # Thu thập dữ liệu
        status = self._market_status(**kwargs)
        sector = self._sector_performance(**kwargs)
        breadth = self._market_breadth(**kwargs)

        # Chấm điểm tổng hợp (0-100, 50 = trung lập)
        score = 50
        reasons = []

        # Index
        vni = status.get("indices", {}).get("VNINDEX", {})
        vni_change = vni.get("change_pct", 0) or 0
        if vni_change > 1:
            score += 15
            reasons.append("VNINDEX tăng mạnh")
        elif vni_change > 0:
            score += 5
            reasons.append("VNINDEX tăng nhẹ")
        elif vni_change > -1:
            score -= 5
            reasons.append("VNINDEX giảm nhẹ")
        else:
            score -= 15
            reasons.append("VNINDEX giảm mạnh")

        # Breadth
        ad = breadth.get("advance_decline", {})
        adv = ad.get("advancing", 0)
        dec = ad.get("declining", 0)
        if adv > dec * 2:
            score += 10
            reasons.append("Breadth rất tích cực")
        elif adv > dec:
            score += 5
            reasons.append("Breadth tích cực")
        elif dec > adv * 2:
            score -= 10
            reasons.append("Breadth rất tiêu cực")
        elif dec > adv:
            score -= 5
            reasons.append("Breadth tiêu cực")

        # Sector — bao nhiêu ngành tăng
        sectors_data = sector.get("sectors", [])
        up_sectors = sum(1 for s in sectors_data if (s.get("avg_change_pct") or 0) > 0)
        down_sectors = len(sectors_data) - up_sectors
        if up_sectors > down_sectors * 2:
            score += 10
            reasons.append(f"{up_sectors}/{len(sectors_data)} ngành tăng")
        elif up_sectors > down_sectors:
            score += 5
        elif down_sectors > up_sectors * 2:
            score -= 10
            reasons.append(f"{down_sectors}/{len(sectors_data)} ngành giảm")

        score = max(0, min(100, score))

        if score >= 70:
            label = "🟢 TÍCH CỰC — Thị trường thuận lợi cho mua vào"
        elif score >= 55:
            label = "🟢 TÍCH CỰC NHẸ — Có thể cân nhắc mua"
        elif score >= 45:
            label = "🟡 TRUNG LẬP — Quan sát thêm"
        elif score >= 30:
            label = "🟠 TIÊU CỰC NHẸ — Cẩn trọng, hạn chế mua"
        else:
            label = "🔴 TIÊU CỰC — Thận trọng, cân nhắc giảm vị thế"

        return {
            "success": True,
            "report": "market_summary",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "market_score": score,
            "assessment": label,
            "reasons": reasons,
            "indices": status.get("indices"),
            "top_gainers": status.get("top_gainers", [])[:5],
            "top_losers": status.get("top_losers", [])[:5],
            "breadth": {
                "advancing": ad.get("advancing"),
                "declining": ad.get("declining"),
                "signal": breadth.get("signal"),
            },
            "sector_ranking": sector.get("sectors", [])[:5],
            "disclaimer": "Đây là phân tích tham khảo, không phải khuyến nghị đầu tư.",
        }
