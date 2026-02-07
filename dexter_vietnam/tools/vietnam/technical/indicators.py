"""
Module 3.1: Technical Indicators
Tính toán các chỉ báo kỹ thuật cho cổ phiếu Việt Nam

Theo CODING_ROADMAP.md - Module 3
Sử dụng thư viện `ta` (Technical Analysis Library in Python)
"""
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
import math
import pandas as pd

try:
    import ta
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
except ImportError:
    ta = None


class TechnicalIndicatorsTool(BaseTool):
    """
    Tính toán chỉ báo kỹ thuật:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - EMA / SMA (Exponential / Simple Moving Average)
    - Stochastic Oscillator
    - ATR (Average True Range)
    """

    # Tham số mặc định
    DEFAULTS = {
        "rsi_window": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "bb_window": 20,
        "bb_std": 2,
        "stoch_window": 14,
        "stoch_smooth": 3,
        "atr_window": 14,
        "sma_windows": [20, 50, 200],
        "ema_windows": [9, 21, 50],
    }

    def __init__(self):
        if ta is None:
            raise ImportError(
                "ta library is not installed. "
                "Install it with: pip install ta"
            )
        self._data_tool = VnstockTool()

    def get_name(self) -> str:
        return "technical_indicators"

    def get_description(self) -> str:
        return (
            "Tính toán chỉ báo kỹ thuật: RSI, MACD, Bollinger Bands, "
            "EMA/SMA, Stochastic Oscillator, ATR."
        )

    async def run(self, symbol: str, action: str = "all", **kwargs) -> Dict[str, Any]:
        """
        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
            action: Chỉ báo cần tính
                - all: Tất cả chỉ báo (mặc định)
                - rsi: RSI
                - macd: MACD
                - bollinger: Bollinger Bands
                - sma: Simple Moving Average
                - ema: Exponential Moving Average
                - stochastic: Stochastic Oscillator
                - atr: Average True Range
                - summary: Tổng hợp giá trị mới nhất + đánh giá
            **kwargs:
                start: Ngày bắt đầu (YYYY-MM-DD)
                end: Ngày kết thúc (YYYY-MM-DD)
                window / period: Chu kỳ tính toán
                last_n: Chỉ trả về N phiên gần nhất
        """
        action_map = {
            "all": self._get_all_indicators,
            "rsi": self._get_rsi,
            "macd": self._get_macd,
            "bollinger": self._get_bollinger,
            "sma": self._get_sma,
            "ema": self._get_ema,
            "stochastic": self._get_stochastic,
            "atr": self._get_atr,
            "summary": self._get_summary,
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

    async def _fetch_price_df(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """Lấy lịch sử giá và trả về DataFrame chuẩn."""
        result = await self._data_tool.get_stock_price(symbol, start=start, end=end)
        if not result.get("success"):
            raise ValueError(result.get("error", "Không lấy được dữ liệu giá"))

        df = pd.DataFrame(result["data"])
        if df.empty:
            raise ValueError("Không có dữ liệu giá")

        # Chuẩn hoá tên cột
        col_map = {
            "time": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def _safe_round(self, val: Any, decimals: int = 4) -> Any:
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return None
        try:
            return round(float(val), decimals)
        except (TypeError, ValueError):
            return val

    def _tail(self, records: List[Dict], last_n: Optional[int] = None) -> List[Dict]:
        """Lấy N bản ghi cuối cùng."""
        if last_n is not None and last_n > 0:
            return records[-last_n:]
        return records

    def _serialize(self, df: pd.DataFrame, columns: List[str], last_n: Optional[int] = None) -> List[Dict]:
        """Chuyển DataFrame thành list of dict, chỉ giữ các cột cần thiết."""
        out = []
        for _, row in df.iterrows():
            record = {"date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None}
            for col in columns:
                record[col] = self._safe_round(row.get(col))
            out.append(record)
        return self._tail(out, last_n)

    # ===================================================================
    # 1. RSI (Relative Strength Index)
    # ===================================================================

    async def _get_rsi(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        RSI - Chỉ số sức mạnh tương đối.
        > 70: Quá mua (overbought) → Có thể giảm
        < 30: Quá bán (oversold) → Có thể tăng
        """
        window = kwargs.get("window", kwargs.get("period", self.DEFAULTS["rsi_window"]))
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        rsi = RSIIndicator(close=df["close"], window=window)
        df["rsi"] = rsi.rsi()

        latest_rsi = self._safe_round(df["rsi"].iloc[-1])
        assessment = self._assess_rsi(latest_rsi)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "RSI",
            "params": {"window": window},
            "latest": {"rsi": latest_rsi, "assessment": assessment},
            "data": self._serialize(df, ["close", "rsi"], last_n),
        }

    def _assess_rsi(self, rsi_val: Any) -> str:
        if rsi_val is None:
            return "N/A"
        if rsi_val > 80:
            return "Quá mua mạnh (>80) ⚠️"
        if rsi_val > 70:
            return "Quá mua (>70) - Cân nhắc chốt lời"
        if rsi_val < 20:
            return "Quá bán mạnh (<20) ⚠️"
        if rsi_val < 30:
            return "Quá bán (<30) - Cân nhắc mua vào"
        if 40 <= rsi_val <= 60:
            return "Trung tính (40-60)"
        if rsi_val > 60:
            return "Thiên tăng (60-70)"
        return "Thiên giảm (30-40)"

    # ===================================================================
    # 2. MACD (Moving Average Convergence Divergence)
    # ===================================================================

    async def _get_macd(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        MACD - Đường trung bình hội tụ phân kỳ.
        Signal: MACD cắt lên Signal Line → Mua | Cắt xuống → Bán
        """
        fast = kwargs.get("fast", self.DEFAULTS["macd_fast"])
        slow = kwargs.get("slow", self.DEFAULTS["macd_slow"])
        signal_w = kwargs.get("signal", self.DEFAULTS["macd_signal"])
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        macd = MACD(close=df["close"], window_fast=fast, window_slow=slow, window_sign=signal_w)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        latest = {
            "macd": self._safe_round(df["macd"].iloc[-1]),
            "signal": self._safe_round(df["macd_signal"].iloc[-1]),
            "histogram": self._safe_round(df["macd_histogram"].iloc[-1]),
        }
        latest["assessment"] = self._assess_macd(df)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "MACD",
            "params": {"fast": fast, "slow": slow, "signal": signal_w},
            "latest": latest,
            "data": self._serialize(df, ["close", "macd", "macd_signal", "macd_histogram"], last_n),
        }

    def _assess_macd(self, df: pd.DataFrame) -> str:
        if len(df) < 2:
            return "Không đủ dữ liệu"
        prev_hist = df["macd_histogram"].iloc[-2]
        curr_hist = df["macd_histogram"].iloc[-1]
        if pd.isna(prev_hist) or pd.isna(curr_hist):
            return "N/A"

        # Kiểm tra crossover
        prev_macd = df["macd"].iloc[-2]
        prev_sig = df["macd_signal"].iloc[-2]
        curr_macd = df["macd"].iloc[-1]
        curr_sig = df["macd_signal"].iloc[-1]

        if not any(pd.isna(v) for v in [prev_macd, prev_sig, curr_macd, curr_sig]):
            if prev_macd <= prev_sig and curr_macd > curr_sig:
                return "🟢 Bullish crossover - MACD cắt lên Signal"
            if prev_macd >= prev_sig and curr_macd < curr_sig:
                return "🔴 Bearish crossover - MACD cắt xuống Signal"

        if curr_hist > 0 and curr_hist > prev_hist:
            return "Tăng mạnh - Histogram dương tăng"
        if curr_hist > 0 and curr_hist < prev_hist:
            return "Tăng yếu dần - Histogram dương giảm"
        if curr_hist < 0 and curr_hist < prev_hist:
            return "Giảm mạnh - Histogram âm tăng"
        if curr_hist < 0 and curr_hist > prev_hist:
            return "Giảm yếu dần - Histogram âm giảm"

        return "Trung tính"

    # ===================================================================
    # 3. Bollinger Bands
    # ===================================================================

    async def _get_bollinger(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Bollinger Bands - Dải Bollinger.
        Giá chạm BB trên → Quá mua | Chạm BB dưới → Quá bán
        Bollinger Width thu hẹp → Sắp breakout
        """
        window = kwargs.get("window", self.DEFAULTS["bb_window"])
        std = kwargs.get("std", self.DEFAULTS["bb_std"])
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        bb = BollingerBands(close=df["close"], window=window, window_dev=std)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_width"] = bb.bollinger_wband()
        df["bb_pband"] = bb.bollinger_pband()  # %B: vị trí giá trong dải

        latest_close = df["close"].iloc[-1]
        latest = {
            "close": self._safe_round(latest_close),
            "upper": self._safe_round(df["bb_upper"].iloc[-1]),
            "middle": self._safe_round(df["bb_middle"].iloc[-1]),
            "lower": self._safe_round(df["bb_lower"].iloc[-1]),
            "width": self._safe_round(df["bb_width"].iloc[-1]),
            "percent_b": self._safe_round(df["bb_pband"].iloc[-1]),
        }
        latest["assessment"] = self._assess_bollinger(latest)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "Bollinger Bands",
            "params": {"window": window, "std": std},
            "latest": latest,
            "data": self._serialize(
                df, ["close", "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pband"], last_n
            ),
        }

    def _assess_bollinger(self, latest: Dict) -> str:
        pband = latest.get("percent_b")
        width = latest.get("width")
        if pband is None:
            return "N/A"

        parts = []
        if pband > 1.0:
            parts.append("Giá trên BB trên → Quá mua ⚠️")
        elif pband > 0.8:
            parts.append("Giá gần BB trên → Thiên tăng")
        elif pband < 0.0:
            parts.append("Giá dưới BB dưới → Quá bán ⚠️")
        elif pband < 0.2:
            parts.append("Giá gần BB dưới → Thiên giảm")
        else:
            parts.append("Giá trong dải BB → Trung tính")

        if width is not None and width < 0.05:
            parts.append("Dải BB thu hẹp → Sắp breakout")

        return " | ".join(parts)

    # ===================================================================
    # 4. SMA (Simple Moving Average)
    # ===================================================================

    async def _get_sma(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """SMA - Đường trung bình giản đơn."""
        windows = kwargs.get("windows", self.DEFAULTS["sma_windows"])
        if isinstance(windows, int):
            windows = [windows]
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        cols = []
        for w in windows:
            col_name = f"sma_{w}"
            sma = SMAIndicator(close=df["close"], window=w)
            df[col_name] = sma.sma_indicator()
            cols.append(col_name)

        latest = {"close": self._safe_round(df["close"].iloc[-1])}
        for col in cols:
            latest[col] = self._safe_round(df[col].iloc[-1])

        latest["assessment"] = self._assess_ma(df, cols, "SMA")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "SMA",
            "params": {"windows": windows},
            "latest": latest,
            "data": self._serialize(df, ["close"] + cols, last_n),
        }

    # ===================================================================
    # 5. EMA (Exponential Moving Average)
    # ===================================================================

    async def _get_ema(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """EMA - Đường trung bình lũy thừa (phản ứng nhanh hơn SMA)."""
        windows = kwargs.get("windows", self.DEFAULTS["ema_windows"])
        if isinstance(windows, int):
            windows = [windows]
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        cols = []
        for w in windows:
            col_name = f"ema_{w}"
            ema = EMAIndicator(close=df["close"], window=w)
            df[col_name] = ema.ema_indicator()
            cols.append(col_name)

        latest = {"close": self._safe_round(df["close"].iloc[-1])}
        for col in cols:
            latest[col] = self._safe_round(df[col].iloc[-1])

        latest["assessment"] = self._assess_ma(df, cols, "EMA")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "EMA",
            "params": {"windows": windows},
            "latest": latest,
            "data": self._serialize(df, ["close"] + cols, last_n),
        }

    def _assess_ma(self, df: pd.DataFrame, cols: List[str], ma_type: str) -> str:
        """Đánh giá tín hiệu MA (dùng cho cả SMA & EMA)."""
        close = df["close"].iloc[-1]
        parts = []

        # Giá so với các MA
        above_count = 0
        for col in cols:
            ma_val = df[col].iloc[-1]
            if pd.notna(ma_val):
                if close > ma_val:
                    above_count += 1

        total = len(cols)
        if above_count == total:
            parts.append(f"Giá trên tất cả {ma_type} → Xu hướng tăng mạnh 🟢")
        elif above_count == 0:
            parts.append(f"Giá dưới tất cả {ma_type} → Xu hướng giảm mạnh 🔴")
        else:
            parts.append(f"Giá trên {above_count}/{total} {ma_type} → Hỗn hợp")

        # Golden Cross / Death Cross (nếu có SMA/EMA 50 & 200)
        short_cols = [c for c in cols if any(str(w) in c for w in [20, 50])]
        long_cols = [c for c in cols if "200" in c]
        if short_cols and long_cols:
            short_val = df[short_cols[0]].iloc[-1]
            long_val = df[long_cols[0]].iloc[-1]
            if pd.notna(short_val) and pd.notna(long_val):
                if len(df) >= 2:
                    prev_short = df[short_cols[0]].iloc[-2]
                    prev_long = df[long_cols[0]].iloc[-2]
                    if pd.notna(prev_short) and pd.notna(prev_long):
                        if prev_short <= prev_long and short_val > long_val:
                            parts.append("🌟 Golden Cross! (MA ngắn cắt lên MA dài)")
                        elif prev_short >= prev_long and short_val < long_val:
                            parts.append("💀 Death Cross! (MA ngắn cắt xuống MA dài)")

        return " | ".join(parts)

    # ===================================================================
    # 6. Stochastic Oscillator
    # ===================================================================

    async def _get_stochastic(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Stochastic Oscillator (%K, %D).
        %K > 80: Quá mua | %K < 20: Quá bán
        %K cắt lên %D → Mua | %K cắt xuống %D → Bán
        """
        window = kwargs.get("window", self.DEFAULTS["stoch_window"])
        smooth = kwargs.get("smooth", self.DEFAULTS["stoch_smooth"])
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        stoch = StochasticOscillator(
            high=df["high"], low=df["low"], close=df["close"],
            window=window, smooth_window=smooth,
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        latest = {
            "k": self._safe_round(df["stoch_k"].iloc[-1]),
            "d": self._safe_round(df["stoch_d"].iloc[-1]),
        }
        latest["assessment"] = self._assess_stochastic(df)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "Stochastic Oscillator",
            "params": {"window": window, "smooth": smooth},
            "latest": latest,
            "data": self._serialize(df, ["close", "stoch_k", "stoch_d"], last_n),
        }

    def _assess_stochastic(self, df: pd.DataFrame) -> str:
        k = df["stoch_k"].iloc[-1]
        d = df["stoch_d"].iloc[-1]
        if pd.isna(k) or pd.isna(d):
            return "N/A"

        parts = []
        # Vùng
        if k > 80:
            parts.append("Quá mua (>80) ⚠️")
        elif k < 20:
            parts.append("Quá bán (<20) ⚠️")
        else:
            parts.append("Trung tính (20-80)")

        # Crossover
        if len(df) >= 2:
            prev_k = df["stoch_k"].iloc[-2]
            prev_d = df["stoch_d"].iloc[-2]
            if pd.notna(prev_k) and pd.notna(prev_d):
                if prev_k <= prev_d and k > d:
                    parts.append("🟢 %K cắt lên %D → Tín hiệu mua")
                elif prev_k >= prev_d and k < d:
                    parts.append("🔴 %K cắt xuống %D → Tín hiệu bán")

        return " | ".join(parts)

    # ===================================================================
    # 7. ATR (Average True Range)
    # ===================================================================

    async def _get_atr(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        ATR - Biên độ dao động trung bình.
        ATR cao → Biến động lớn | ATR thấp → Ít biến động
        Hữu ích cho Stop-loss & Position sizing.
        """
        window = kwargs.get("window", self.DEFAULTS["atr_window"])
        last_n = kwargs.get("last_n")
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=window)
        df["atr"] = atr.average_true_range()

        latest_atr = self._safe_round(df["atr"].iloc[-1])
        latest_close = self._safe_round(df["close"].iloc[-1])

        # ATR % so với giá đóng cửa
        atr_pct = None
        if latest_atr and latest_close and latest_close > 0:
            atr_pct = self._safe_round(latest_atr / latest_close * 100, 2)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "ATR",
            "params": {"window": window},
            "latest": {
                "atr": latest_atr,
                "close": latest_close,
                "atr_percent": atr_pct,
                "assessment": self._assess_atr(atr_pct),
                "suggested_stop_loss": self._safe_round(
                    latest_close - 2 * latest_atr if latest_close and latest_atr else None
                ),
            },
            "data": self._serialize(df, ["close", "atr"], last_n),
        }

    def _assess_atr(self, atr_pct: Any) -> str:
        if atr_pct is None:
            return "N/A"
        if atr_pct > 5:
            return f"Biến động rất cao ({atr_pct}%) ⚠️"
        if atr_pct > 3:
            return f"Biến động cao ({atr_pct}%)"
        if atr_pct > 1.5:
            return f"Biến động trung bình ({atr_pct}%)"
        return f"Biến động thấp ({atr_pct}%)"

    # ===================================================================
    # 8. ALL - Tất cả chỉ báo
    # ===================================================================

    async def _get_all_indicators(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Tính toán tất cả chỉ báo kỹ thuật trên cùng 1 bộ dữ liệu."""
        last_n = kwargs.get("last_n", 30)
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        # RSI
        rsi_w = kwargs.get("rsi_window", self.DEFAULTS["rsi_window"])
        rsi = RSIIndicator(close=df["close"], window=rsi_w)
        df["rsi"] = rsi.rsi()

        # MACD
        macd = MACD(
            close=df["close"],
            window_fast=self.DEFAULTS["macd_fast"],
            window_slow=self.DEFAULTS["macd_slow"],
            window_sign=self.DEFAULTS["macd_signal"],
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        # Bollinger Bands
        bb = BollingerBands(
            close=df["close"],
            window=self.DEFAULTS["bb_window"],
            window_dev=self.DEFAULTS["bb_std"],
        )
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_pband"] = bb.bollinger_pband()

        # SMA
        for w in self.DEFAULTS["sma_windows"]:
            sma = SMAIndicator(close=df["close"], window=w)
            df[f"sma_{w}"] = sma.sma_indicator()

        # EMA
        for w in self.DEFAULTS["ema_windows"]:
            ema = EMAIndicator(close=df["close"], window=w)
            df[f"ema_{w}"] = ema.ema_indicator()

        # Stochastic
        stoch = StochasticOscillator(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.DEFAULTS["stoch_window"],
            smooth_window=self.DEFAULTS["stoch_smooth"],
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # ATR
        atr = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.DEFAULTS["atr_window"],
        )
        df["atr"] = atr.average_true_range()

        # Serialize tất cả
        all_cols = [
            "close", "volume", "rsi",
            "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "bb_pband",
            "stoch_k", "stoch_d", "atr",
        ]
        all_cols += [f"sma_{w}" for w in self.DEFAULTS["sma_windows"]]
        all_cols += [f"ema_{w}" for w in self.DEFAULTS["ema_windows"]]

        return {
            "success": True,
            "symbol": symbol.upper(),
            "indicator": "all",
            "count": len(df),
            "data": self._serialize(df, all_cols, last_n),
        }

    # ===================================================================
    # 9. SUMMARY - Tổng hợp mới nhất + Đánh giá
    # ===================================================================

    async def _get_summary(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Trả về snapshot giá trị mới nhất của mọi chỉ báo + đánh giá tổng hợp."""
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        r = self._safe_round

        # RSI
        rsi = RSIIndicator(close=df["close"], window=self.DEFAULTS["rsi_window"])
        df["rsi"] = rsi.rsi()

        # MACD
        macd = MACD(
            close=df["close"],
            window_fast=self.DEFAULTS["macd_fast"],
            window_slow=self.DEFAULTS["macd_slow"],
            window_sign=self.DEFAULTS["macd_signal"],
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        # Bollinger Bands
        bb = BollingerBands(
            close=df["close"],
            window=self.DEFAULTS["bb_window"],
            window_dev=self.DEFAULTS["bb_std"],
        )
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_pband"] = bb.bollinger_pband()

        # SMA
        for w in self.DEFAULTS["sma_windows"]:
            sma_ind = SMAIndicator(close=df["close"], window=w)
            df[f"sma_{w}"] = sma_ind.sma_indicator()

        # Stochastic
        stoch = StochasticOscillator(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.DEFAULTS["stoch_window"],
            smooth_window=self.DEFAULTS["stoch_smooth"],
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # ATR
        atr_ind = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"],
            window=self.DEFAULTS["atr_window"],
        )
        df["atr"] = atr_ind.average_true_range()

        close_val = r(df["close"].iloc[-1])
        rsi_val = r(df["rsi"].iloc[-1])
        atr_val = r(df["atr"].iloc[-1])
        atr_pct = r(atr_val / close_val * 100, 2) if atr_val and close_val else None

        # Tính điểm tổng hợp (bullish / bearish / neutral)
        score = self._compute_overall_score(df)

        sma_cols = [f"sma_{w}" for w in self.DEFAULTS["sma_windows"]]
        latest_sma = {col: r(df[col].iloc[-1]) for col in sma_cols}

        summary = {
            "date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
            "close": close_val,
            "rsi": {"value": rsi_val, "assessment": self._assess_rsi(rsi_val)},
            "macd": {
                "macd": r(df["macd"].iloc[-1]),
                "signal": r(df["macd_signal"].iloc[-1]),
                "histogram": r(df["macd_histogram"].iloc[-1]),
                "assessment": self._assess_macd(df),
            },
            "bollinger": {
                "upper": r(df["bb_upper"].iloc[-1]),
                "lower": r(df["bb_lower"].iloc[-1]),
                "percent_b": r(df["bb_pband"].iloc[-1]),
                "assessment": self._assess_bollinger({
                    "percent_b": r(df["bb_pband"].iloc[-1]),
                    "width": None,
                }),
            },
            "sma": latest_sma,
            "stochastic": {
                "k": r(df["stoch_k"].iloc[-1]),
                "d": r(df["stoch_d"].iloc[-1]),
                "assessment": self._assess_stochastic(df),
            },
            "atr": {
                "value": atr_val,
                "percent": atr_pct,
                "assessment": self._assess_atr(atr_pct),
            },
            "overall_score": score,
        }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "technical_summary",
            "data": summary,
        }

    def _compute_overall_score(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Tính điểm tổng hợp:
        +1: Tín hiệu tăng | -1: Tín hiệu giảm | 0: Trung tính
        """
        signals = []
        close = df["close"].iloc[-1]

        # RSI
        rsi_val = df["rsi"].iloc[-1]
        if pd.notna(rsi_val):
            if rsi_val < 30:
                signals.append(("RSI quá bán", +1))
            elif rsi_val > 70:
                signals.append(("RSI quá mua", -1))
            else:
                signals.append(("RSI trung tính", 0))

        # MACD histogram
        hist = df["macd_histogram"].iloc[-1]
        if pd.notna(hist):
            if hist > 0:
                signals.append(("MACD histogram dương", +1))
            else:
                signals.append(("MACD histogram âm", -1))

        # Bollinger %B
        pband = df["bb_pband"].iloc[-1]
        if pd.notna(pband):
            if pband < 0.2:
                signals.append(("BB gần dải dưới", +1))
            elif pband > 0.8:
                signals.append(("BB gần dải trên", -1))
            else:
                signals.append(("BB trung tính", 0))

        # Stochastic
        k = df["stoch_k"].iloc[-1]
        if pd.notna(k):
            if k < 20:
                signals.append(("Stochastic quá bán", +1))
            elif k > 80:
                signals.append(("Stochastic quá mua", -1))
            else:
                signals.append(("Stochastic trung tính", 0))

        # SMA - Giá so với SMA 20/50/200
        for w in self.DEFAULTS["sma_windows"]:
            col = f"sma_{w}"
            if col in df.columns:
                ma_val = df[col].iloc[-1]
                if pd.notna(ma_val):
                    if close > ma_val:
                        signals.append((f"Giá > SMA{w}", +1))
                    else:
                        signals.append((f"Giá < SMA{w}", -1))

        total = sum(s[1] for s in signals)
        max_score = len(signals)

        if max_score == 0:
            verdict = "Không đủ dữ liệu"
        elif total >= max_score * 0.5:
            verdict = "🟢 TĂNG MẠNH (Strong Bullish)"
        elif total > 0:
            verdict = "🟢 THIÊN TĂNG (Bullish)"
        elif total <= -max_score * 0.5:
            verdict = "🔴 GIẢM MẠNH (Strong Bearish)"
        elif total < 0:
            verdict = "🔴 THIÊN GIẢM (Bearish)"
        else:
            verdict = "🟡 TRUNG TÍNH (Neutral)"

        return {
            "score": total,
            "max_score": max_score,
            "verdict": verdict,
            "details": [{"signal": s[0], "value": s[1]} for s in signals],
        }
