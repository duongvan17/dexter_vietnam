
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import math
import pandas as pd


class MoneyFlowTool(BaseTool):

    def __init__(self):
        self._data_tool = VnstockTool()

    def get_name(self) -> str:
        return "money_flow"

    def get_description(self) -> str:
        return (
            "Theo dõi dòng tiền: khối ngoại mua/bán ròng, tự doanh, "
            "giao dịch nội bộ, top mã được mua/bán nhiều nhất."
        )

    def get_actions(self) -> dict:
        return {
            "flow_analysis": "Phân tích dòng tiền tổng hợp (OBV, A/D, MFI) cho 1 mã",
            "foreign": "Giao dịch khối ngoại của 1 mã cụ thể",
            "foreign_history": "Lịch sử volume + phiên tăng/giảm — proxy dòng tiền ngoại",
            "top_foreign_buy": "Top mã khối ngoại mua ròng nhiều nhất (scan blue-chip)",
            "top_foreign_sell": "Top mã khối ngoại bán ròng nhiều nhất (scan blue-chip)",
            "proprietary": "Giao dịch tự doanh CTCK của 1 mã",
            "insider": "Giao dịch nội bộ: cổ đông lớn, HĐQT",
        }

    def get_parameters_schema(self) -> dict:
        symbol_param = {
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Mã cổ phiếu (VD: FPT, VNM, HPG)",
                }
            },
            "required": ["symbol"],
        }
        no_param = {"properties": {}, "required": []}
        return {
            "flow_analysis": symbol_param,
            "foreign": symbol_param,
            "foreign_history": symbol_param,
            "top_foreign_buy": no_param,
            "top_foreign_sell": no_param,
            "proprietary": symbol_param,
            "insider": symbol_param,
        }


    def run(self, symbol: str = "", action: str = "foreign", **kwargs) -> Dict[str, Any]:

        action_map = {
            "foreign": self._get_foreign_trading,
            "foreign_history": self._get_foreign_history,
            "top_foreign_buy": self._get_top_foreign_buying,
            "top_foreign_sell": self._get_top_foreign_selling,
            "proprietary": self._get_proprietary_trading,
            "insider": self._get_insider_trading,
            "flow_analysis": self._get_flow_analysis,
            "analyze": self._get_flow_analysis,  # Alias for flow_analysis
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}. Dùng: {list(action_map.keys())}"}
        try:
            return action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _safe_round(self, val: Any, decimals: int = 2) -> Any:
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return None
        try:
            return round(float(val), decimals)
        except (TypeError, ValueError):
            return val

    def _convert_timestamps(self, records: List[Dict]) -> List[Dict]:
        """Chuyển tất cả Timestamp/datetime thành string."""
        for record in records:
            for key, val in record.items():
                if hasattr(val, 'strftime'):
                    record[key] = val.strftime('%Y-%m-%d')
                elif isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                    record[key] = None
        return records

    def _fetch_price_data(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """Lấy dữ liệu giá (dùng cho phân tích volume & price action)."""
        result = self._data_tool.get_stock_price(symbol, start=start, end=end)
        if not result.get("success"):
            raise ValueError(result.get("error", "Không lấy được dữ liệu giá"))
        df = pd.DataFrame(result["data"])
        if df.empty:
            raise ValueError("Không có dữ liệu giá")
        col_map = {"time": "date"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df


    def _get_foreign_trading(self, symbol: str, **kwargs) -> Dict[str, Any]:

        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        result = self._data_tool.get_foreign_trading(symbol)
        if not result.get("success"):
            return result

        raw_data = result.get("data", [])

        # Phân tích dữ liệu trading
        if isinstance(raw_data, list) and raw_data:
            records = self._convert_timestamps(raw_data)

            # Tìm thông tin khối ngoại trong dữ liệu
            summary = self._extract_foreign_summary(records)

            return {
                "success": True,
                "symbol": symbol.upper(),
                "report": "foreign_trading",
                "summary": summary,
                "data": records[-20:],  # 20 bản ghi gần nhất
            }
        elif isinstance(raw_data, dict):
            return {
                "success": True,
                "symbol": symbol.upper(),
                "report": "foreign_trading",
                "data": raw_data,
            }
        else:
            return {
                "success": True,
                "symbol": symbol.upper(),
                "report": "foreign_trading",
                "data": raw_data,
                "note": "Dữ liệu có thể cần xử lý thêm tuỳ cấu trúc vnstock trả về",
            }

    def _extract_foreign_summary(self, records: List[Dict]) -> Dict[str, Any]:
        """Trích xuất thông tin tóm tắt khối ngoại từ raw data."""
        summary = {}

        if not records:
            return summary

        # Thử tìm các cột phổ biến liên quan đến khối ngoại
        sample = records[0]
        keys = [k.lower() if isinstance(k, str) else str(k) for k in sample.keys()]

        # Tìm cột buy/sell volume
        buy_keys = [k for k in sample.keys() if any(
            term in str(k).lower() for term in ["buy", "mua", "foreign_buy", "nn_mua"]
        )]
        sell_keys = [k for k in sample.keys() if any(
            term in str(k).lower() for term in ["sell", "bán", "ban", "foreign_sell", "nn_ban"]
        )]

        if buy_keys:
            total_buy = sum(
                r.get(buy_keys[0], 0) or 0 for r in records
                if isinstance(r.get(buy_keys[0]), (int, float))
            )
            summary["total_buy_volume"] = self._safe_round(total_buy, 0)

        if sell_keys:
            total_sell = sum(
                r.get(sell_keys[0], 0) or 0 for r in records
                if isinstance(r.get(sell_keys[0]), (int, float))
            )
            summary["total_sell_volume"] = self._safe_round(total_sell, 0)

        if "total_buy_volume" in summary and "total_sell_volume" in summary:
            net = (summary["total_buy_volume"] or 0) - (summary["total_sell_volume"] or 0)
            summary["net_volume"] = self._safe_round(net, 0)
            summary["net_direction"] = "MUA RÒNG 🟢" if net > 0 else ("BÁN RÒNG 🔴" if net < 0 else "TRUNG TÍNH")

        summary["available_columns"] = list(sample.keys())
        return summary


    def _get_foreign_history(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phân tích lịch sử giao dịch khối ngoại theo thời gian.
        Kết hợp dữ liệu giá + volume để nhận diện xu hướng dòng tiền.
        """
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        start = kwargs.get("start")
        end = kwargs.get("end")

        # Lấy dữ liệu giá (bao gồm volume)
        df = self._fetch_price_data(symbol, start, end)

        # Phân tích volume trend
        df["volume_sma20"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma20"]

        # Phát hiện volume đột biến (>1.5x trung bình)
        df["volume_spike"] = df["volume_ratio"] > 1.5

        # Phân loại phiên tăng/giảm
        df["price_change"] = df["close"].pct_change()
        df["session_type"] = df.apply(
            lambda row: "UP" if row.get("close", 0) > row.get("open", 0) else "DOWN",
            axis=1,
        )

        # Volume theo phiên tăng vs phiên giảm (proxy dòng tiền)
        recent = df.tail(20)
        up_sessions = recent[recent["session_type"] == "UP"]
        down_sessions = recent[recent["session_type"] == "DOWN"]

        up_volume = up_sessions["volume"].sum() if not up_sessions.empty else 0
        down_volume = down_sessions["volume"].sum() if not down_sessions.empty else 0
        total_volume = up_volume + down_volume

        # Money Flow Ratio
        mf_ratio = up_volume / down_volume if down_volume > 0 else float('inf')

        if mf_ratio > 1.5:
            flow_assessment = "🟢 Dòng tiền vào mạnh (Volume phiên tăng >> phiên giảm)"
        elif mf_ratio > 1.0:
            flow_assessment = "🟢 Dòng tiền vào nhẹ"
        elif mf_ratio > 0.67:
            flow_assessment = "🔴 Dòng tiền ra nhẹ"
        else:
            flow_assessment = "🔴 Dòng tiền ra mạnh (Volume phiên giảm >> phiên tăng)"

        # Volume spikes gần đây
        spikes = df[df["volume_spike"]].tail(5)
        spike_list = []
        for _, row in spikes.iterrows():
            spike_list.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "volume": int(row["volume"]),
                "volume_ratio": self._safe_round(row["volume_ratio"]),
                "session": row["session_type"],
                "price_change": self._safe_round(row["price_change"] * 100, 2),
            })

        # Lấy thêm dữ liệu khối ngoại nếu có
        foreign_result = self._data_tool.get_foreign_trading(symbol)
        foreign_data = None
        if foreign_result.get("success"):
            foreign_data = foreign_result.get("data")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "foreign_history",
            "period": {
                "start": df["date"].iloc[0].strftime("%Y-%m-%d"),
                "end": df["date"].iloc[-1].strftime("%Y-%m-%d"),
                "total_sessions": len(df),
            },
            "volume_analysis": {
                "up_sessions": len(up_sessions),
                "down_sessions": len(down_sessions),
                "up_volume": int(up_volume),
                "down_volume": int(down_volume),
                "money_flow_ratio": self._safe_round(mf_ratio) if mf_ratio != float('inf') else "∞",
                "assessment": flow_assessment,
            },
            "volume_spikes": spike_list,
            "foreign_raw": foreign_data,
        }


    def _get_top_foreign_buying(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """
        Top N mã cổ phiếu khối ngoại mua ròng nhiều nhất.
        Scan các mã lớn trên HOSE để tìm dòng tiền ngoại.
        """
        top_n = kwargs.get("top_n", 10)

        # Lấy danh sách blue-chip phổ biến để scan
        major_symbols = [
            "VNM", "VCB", "FPT", "VHM", "VIC", "HPG", "MSN", "MBB",
            "TCB", "VPB", "ACB", "BID", "CTG", "STB", "SSI", "HDB",
            "MWG", "PNJ", "REE", "GAS", "PLX", "POW", "SAB", "VRE",
            "NVL", "KDH", "DGC", "GVR", "BCM", "VJC",
        ]

        results = []
        for sym in major_symbols:
            try:
                foreign_result = self._data_tool.get_foreign_trading(sym)
                if foreign_result.get("success"):
                    data = foreign_result.get("data", [])
                    summary = self._extract_foreign_net(sym, data)
                    if summary:
                        results.append(summary)
            except Exception:
                continue

        # Sắp xếp theo net volume (mua ròng giảm dần)
        results.sort(key=lambda x: x.get("net_value", 0), reverse=True)
        top_buy = results[:top_n]

        return {
            "success": True,
            "report": "top_foreign_buying",
            "top_n": top_n,
            "scanned": len(major_symbols),
            "data": top_buy,
            "note": "Dựa trên dữ liệu giao dịch gần nhất từ vnstock",
        }


    def _get_top_foreign_selling(self, symbol: str = "", **kwargs) -> Dict[str, Any]:
        """Top N mã cổ phiếu khối ngoại bán ròng nhiều nhất."""
        top_n = kwargs.get("top_n", 10)

        major_symbols = [
            "VNM", "VCB", "FPT", "VHM", "VIC", "HPG", "MSN", "MBB",
            "TCB", "VPB", "ACB", "BID", "CTG", "STB", "SSI", "HDB",
            "MWG", "PNJ", "REE", "GAS", "PLX", "POW", "SAB", "VRE",
            "NVL", "KDH", "DGC", "GVR", "BCM", "VJC",
        ]

        results = []
        for sym in major_symbols:
            try:
                foreign_result = self._data_tool.get_foreign_trading(sym)
                if foreign_result.get("success"):
                    data = foreign_result.get("data", [])
                    summary = self._extract_foreign_net(sym, data)
                    if summary:
                        results.append(summary)
            except Exception:
                continue

        # Sắp xếp theo net volume (bán ròng tăng dần = giá trị âm nhất trước)
        results.sort(key=lambda x: x.get("net_value", 0))
        top_sell = results[:top_n]

        return {
            "success": True,
            "report": "top_foreign_selling",
            "top_n": top_n,
            "scanned": len(major_symbols),
            "data": top_sell,
            "note": "Dựa trên dữ liệu giao dịch gần nhất từ vnstock",
        }

    def _extract_foreign_net(self, symbol: str, data: Any) -> Optional[Dict]:
        """Trích xuất thông tin mua/bán ròng từ raw data."""
        if not data:
            return None

        if isinstance(data, list) and data:
            sample = data[0] if data else {}
        elif isinstance(data, dict):
            sample = data
        else:
            return None

        # Tìm cột buy/sell
        buy_val = None
        sell_val = None

        for key, val in sample.items():
            key_str = str(key).lower()
            if any(t in key_str for t in ["buy", "mua"]) and isinstance(val, (int, float)):
                buy_val = val
            if any(t in key_str for t in ["sell", "bán", "ban"]) and isinstance(val, (int, float)):
                sell_val = val

        if buy_val is not None and sell_val is not None:
            net = buy_val - sell_val
            return {
                "symbol": symbol.upper(),
                "buy_volume": self._safe_round(buy_val, 0),
                "sell_volume": self._safe_round(sell_val, 0),
                "net_value": self._safe_round(net, 0),
                "direction": "MUA RÒNG 🟢" if net > 0 else ("BÁN RÒNG 🔴" if net < 0 else "—"),
            }

        # Fallback: trả về raw data
        return {
            "symbol": symbol.upper(),
            "raw": sample,
            "net_value": 0,
        }


    def _get_proprietary_trading(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Giao dịch tự doanh của CTCK.
        Tự doanh mua ròng → CTCK kỳ vọng giá tăng.
        """
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        try:
            stock = self._data_tool._get_stock(symbol)

            # Thử lấy dữ liệu tự doanh từ vnstock
            prop_data = None
            for method_name in ["proprietary_trading", "insider_deal"]:
                try:
                    method = getattr(stock.trading, method_name, None)
                    if method:
                        prop_data = method()
                        break
                except (AttributeError, Exception):
                    continue

            if prop_data is not None:
                if isinstance(prop_data, pd.DataFrame) and not prop_data.empty:
                    records = prop_data.to_dict("records")
                    records = self._convert_timestamps(records)

                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "report": "proprietary_trading",
                        "count": len(records),
                        "data": records[-20:],
                    }
                elif isinstance(prop_data, (dict, list)):
                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "report": "proprietary_trading",
                        "data": prop_data,
                    }

            # Fallback: phân tích volume bất thường như proxy
            return self._proprietary_proxy(symbol, **kwargs)

        except Exception as e:
            return self._proprietary_proxy(symbol, **kwargs)

    def _proprietary_proxy(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Proxy phân tích tự doanh: phát hiện volume đột biến + biến động giá nhỏ
        (dấu hiệu của giao dịch tổ chức / block trade).
        """
        df = self._fetch_price_data(symbol)
        df["volume_sma20"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma20"]
        df["price_change_pct"] = df["close"].pct_change().abs() * 100
        df["body_pct"] = ((df["close"] - df["open"]).abs() / df["open"]) * 100

        # Dấu hiệu tổ chức: volume cao + biến động giá nhỏ
        institutional_mask = (df["volume_ratio"] > 2.0) & (df["body_pct"] < 1.0)
        institutional = df[institutional_mask].tail(10)

        inst_list = []
        for _, row in institutional.iterrows():
            inst_list.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "volume": int(row["volume"]),
                "volume_ratio": self._safe_round(row["volume_ratio"]),
                "price_change_pct": self._safe_round(row["price_change_pct"]),
                "note": "Volume cao + biến động giá nhỏ → Có thể giao dịch tổ chức",
            })

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "proprietary_proxy",
            "note": "Dữ liệu tự doanh trực tiếp không khả dụng. "
                    "Phân tích proxy dựa trên volume + price action.",
            "institutional_signals": inst_list,
            "total_detected": len(inst_list),
        }


    def _get_insider_trading(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Giao dịch nội bộ: cổ đông lớn, HĐQT, Ban Giám đốc.
        Nội bộ mua → Tin tưởng tương lai | Bán → Cần cảnh giác.
        """
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        try:
            stock = self._data_tool._get_stock(symbol)

            # Thử lấy dữ liệu giao dịch nội bộ
            insider_data = None
            for method_name in ["insider_deal", "insider_trading", "major_holder"]:
                try:
                    method = getattr(stock.trading, method_name, None)
                    if method:
                        insider_data = method()
                        break
                except (AttributeError, Exception):
                    continue

            # Thử từ company
            if insider_data is None:
                for method_name in ["insider_deal", "major_holder", "shareholders"]:
                    try:
                        method = getattr(stock.company, method_name, None)
                        if method:
                            insider_data = method()
                            break
                    except (AttributeError, Exception):
                        continue

            if insider_data is not None:
                if isinstance(insider_data, pd.DataFrame) and not insider_data.empty:
                    records = insider_data.to_dict("records")
                    records = self._convert_timestamps(records)

                    # Phân tích xu hướng nội bộ
                    analysis = self._analyze_insider(records)

                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "report": "insider_trading",
                        "count": len(records),
                        "analysis": analysis,
                        "data": records[-20:],
                    }
                elif isinstance(insider_data, (dict, list)):
                    return {
                        "success": True,
                        "symbol": symbol.upper(),
                        "report": "insider_trading",
                        "data": insider_data,
                    }

            return {
                "success": True,
                "symbol": symbol.upper(),
                "report": "insider_trading",
                "data": [],
                "note": "Dữ liệu giao dịch nội bộ không khả dụng qua vnstock. "
                        "Kiểm tra tại: https://cafef.vn hoặc https://vietstock.vn",
            }

        except Exception as e:
            return {
                "success": False,
                "symbol": symbol.upper(),
                "error": f"Lỗi lấy giao dịch nội bộ: {str(e)}",
            }

    def _analyze_insider(self, records: List[Dict]) -> Dict[str, Any]:
        """Phân tích xu hướng giao dịch nội bộ."""
        buy_count = 0
        sell_count = 0

        for r in records:
            for key, val in r.items():
                key_str = str(key).lower()
                val_str = str(val).lower() if val else ""
                if "type" in key_str or "loai" in key_str or "action" in key_str:
                    if any(t in val_str for t in ["buy", "mua"]):
                        buy_count += 1
                    elif any(t in val_str for t in ["sell", "bán", "ban"]):
                        sell_count += 1

        if buy_count + sell_count == 0:
            sentiment = "Không đủ dữ liệu phân tích"
        elif buy_count > sell_count * 1.5:
            sentiment = "🟢 Nội bộ MUA nhiều hơn BÁN → Tín hiệu tích cực"
        elif sell_count > buy_count * 1.5:
            sentiment = "🔴 Nội bộ BÁN nhiều hơn MUA → Cần cảnh giác"
        else:
            sentiment = "🟡 Giao dịch nội bộ cân bằng"

        return {
            "buy_transactions": buy_count,
            "sell_transactions": sell_count,
            "sentiment": sentiment,
        }


    def _get_flow_analysis(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phân tích dòng tiền tổng hợp cho 1 mã:
        - Volume trend (20 phiên)
        - Money Flow Index (MFI) proxy
        - On-Balance Volume (OBV)
        - Accumulation/Distribution
        - Khối ngoại
        """
        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        df = self._fetch_price_data(symbol, kwargs.get("start"), kwargs.get("end"))

        r = self._safe_round

        # --- Volume Trend ---
        df["volume_sma5"] = df["volume"].rolling(5).mean()
        df["volume_sma20"] = df["volume"].rolling(20).mean()
        vol_trend = "TĂNG" if df["volume_sma5"].iloc[-1] > df["volume_sma20"].iloc[-1] else "GIẢM"

        # --- On-Balance Volume (OBV) ---
        df["obv"] = 0.0
        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                df.loc[df.index[i], "obv"] = df["obv"].iloc[i - 1] + df["volume"].iloc[i]
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                df.loc[df.index[i], "obv"] = df["obv"].iloc[i - 1] - df["volume"].iloc[i]
            else:
                df.loc[df.index[i], "obv"] = df["obv"].iloc[i - 1]

        # OBV trend
        obv_sma10 = df["obv"].rolling(10).mean()
        obv_trend = "TĂNG" if df["obv"].iloc[-1] > obv_sma10.iloc[-1] else "GIẢM"

        # --- Accumulation/Distribution (A/D) ---
        df["ad_multiplier"] = (
            ((df["close"] - df["low"]) - (df["high"] - df["close"]))
            / (df["high"] - df["low"]).replace(0, 1)
        )
        df["ad_volume"] = df["ad_multiplier"] * df["volume"]
        df["ad_line"] = df["ad_volume"].cumsum()

        ad_sma10 = df["ad_line"].rolling(10).mean()
        ad_trend = "TÍCH LŨY 🟢" if df["ad_line"].iloc[-1] > ad_sma10.iloc[-1] else "PHÂN PHỐI 🔴"

        # --- Money Flow Index (MFI) proxy ---
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]
        df["mf_positive"] = 0.0
        df["mf_negative"] = 0.0
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i - 1]:
                df.loc[df.index[i], "mf_positive"] = money_flow.iloc[i]
            else:
                df.loc[df.index[i], "mf_negative"] = money_flow.iloc[i]

        period = 14
        pos_sum = df["mf_positive"].rolling(period).sum()
        neg_sum = df["mf_negative"].rolling(period).sum()
        mf_ratio = pos_sum / neg_sum.replace(0, 1)
        mfi = 100 - (100 / (1 + mf_ratio))
        current_mfi = r(mfi.iloc[-1])

        if current_mfi is not None:
            if current_mfi > 80:
                mfi_assessment = "Quá mua (>80) ⚠️"
            elif current_mfi > 60:
                mfi_assessment = "Dòng tiền vào mạnh 🟢"
            elif current_mfi < 20:
                mfi_assessment = "Quá bán (<20) ⚠️"
            elif current_mfi < 40:
                mfi_assessment = "Dòng tiền ra mạnh 🔴"
            else:
                mfi_assessment = "Trung tính"
        else:
            mfi_assessment = "N/A"

        # --- Phiên tăng vs giảm (20 phiên gần nhất) ---
        recent = df.tail(20)
        up_sessions = len(recent[recent["close"] > recent["open"]])
        down_sessions = len(recent[recent["close"] < recent["open"]])

        # Khối ngoại
        foreign = self._data_tool.get_foreign_trading(symbol)
        foreign_summary = None
        if foreign.get("success"):
            raw = foreign.get("data", [])
            if isinstance(raw, list) and raw:
                foreign_summary = self._extract_foreign_summary(raw)

        # --- Tổng hợp ---
        signals = []
        if vol_trend == "TĂNG":
            signals.append(("Volume tăng", +1))
        else:
            signals.append(("Volume giảm", -1))

        if obv_trend == "TĂNG":
            signals.append(("OBV tăng", +1))
        else:
            signals.append(("OBV giảm", -1))

        if "TÍCH LŨY" in ad_trend:
            signals.append(("A/D tích luỹ", +1))
        else:
            signals.append(("A/D phân phối", -1))

        if current_mfi and current_mfi > 50:
            signals.append(("MFI > 50", +1))
        elif current_mfi:
            signals.append(("MFI < 50", -1))

        total_score = sum(s[1] for s in signals)
        if total_score >= 3:
            overall = "🟢 DÒNG TIỀN VÀO MẠNH"
        elif total_score >= 1:
            overall = "🟢 DÒNG TIỀN VÀO"
        elif total_score <= -3:
            overall = "🔴 DÒNG TIỀN RA MẠNH"
        elif total_score <= -1:
            overall = "🔴 DÒNG TIỀN RA"
        else:
            overall = "🟡 TRUNG TÍNH"

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "flow_analysis",
            "close": r(df["close"].iloc[-1]),
            "analysis": {
                "volume_trend": vol_trend,
                "obv_trend": obv_trend,
                "ad_trend": ad_trend,
                "mfi": {"value": current_mfi, "assessment": mfi_assessment},
                "recent_sessions": {
                    "up": up_sessions,
                    "down": down_sessions,
                    "total": 20,
                },
            },
            "foreign": foreign_summary,
            "overall": overall,
            "score": {
                "value": total_score,
                "max": len(signals),
                "details": [{"signal": s[0], "value": s[1]} for s in signals],
            },
        }
