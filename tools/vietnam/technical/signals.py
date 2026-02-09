"""
Module 3.2: Trading Signals
Phát hiện tín hiệu giao dịch dựa trên chỉ báo kỹ thuật

Theo CODING_ROADMAP.md - Module 3
"""
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from dexter_vietnam.tools.vietnam.technical.indicators import TechnicalIndicatorsTool
from typing import Dict, Any, Optional, List, Tuple
import math
import pandas as pd

try:
    import ta
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
except ImportError:
    ta = None


class TradingSignalsTool(BaseTool):
    """
    Phát hiện tín hiệu giao dịch:
    - RSI overbought / oversold
    - MACD crossover (bullish / bearish)
    - Golden Cross / Death Cross
    - Support / Resistance levels
    - Trend detection (xu hướng)
    - Tổng hợp tín hiệu → khuyến nghị
    """

    def __init__(self):
        if ta is None:
            raise ImportError(
                "ta library is not installed. "
                "Install it with: pip install ta"
            )
        self._data_tool = VnstockTool()
        self._indicator_tool = TechnicalIndicatorsTool()

    def get_name(self) -> str:
        return "trading_signals"

    def get_description(self) -> str:
        return (
            "Phát hiện tín hiệu giao dịch: RSI overbought/oversold, "
            "MACD crossover, Golden/Death Cross, Support/Resistance, Trend."
        )

    async def run(self, symbol: str, action: str = "all", **kwargs) -> Dict[str, Any]:
        """
        Args:
            symbol: Mã cổ phiếu (VD: VNM, FPT, VCB)
            action: Loại tín hiệu
                - all: Tất cả tín hiệu (mặc định)
                - rsi_signals: Tín hiệu RSI
                - macd_signals: Tín hiệu MACD crossover
                - ma_cross: Golden Cross / Death Cross
                - support_resistance: Vùng hỗ trợ / kháng cự
                - trend: Phát hiện xu hướng
                - recommendation: Khuyến nghị tổng hợp
            **kwargs:
                start: Ngày bắt đầu (YYYY-MM-DD)
                end: Ngày kết thúc (YYYY-MM-DD)
                lookback: Số phiên nhìn lại để tìm tín hiệu
        """
        action_map = {
            "all": self._get_all_signals,
            "rsi_signals": self._get_rsi_signals,
            "macd_signals": self._get_macd_signals,
            "ma_cross": self._get_ma_cross_signals,
            "support_resistance": self._get_support_resistance,
            "trend": self._get_trend,
            "recommendation": self._get_recommendation,
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

        col_map = {"time": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}
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

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Thêm tất cả chỉ báo kỹ thuật vào DataFrame."""
        # RSI
        rsi = RSIIndicator(close=df["close"], window=14)
        df["rsi"] = rsi.rsi()

        # MACD
        macd = MACD(close=df["close"], window_fast=12, window_slow=26, window_sign=9)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        # SMA
        for w in [20, 50, 200]:
            sma = SMAIndicator(close=df["close"], window=w)
            df[f"sma_{w}"] = sma.sma_indicator()

        # EMA
        for w in [9, 21, 50]:
            ema = EMAIndicator(close=df["close"], window=w)
            df[f"ema_{w}"] = ema.ema_indicator()

        # Bollinger Bands
        bb = BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_pband"] = bb.bollinger_pband()

        # Stochastic
        stoch = StochasticOscillator(high=df["high"], low=df["low"], close=df["close"], window=14, smooth_window=3)
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # ATR
        atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14)
        df["atr"] = atr.average_true_range()

        return df

    # ===================================================================
    # 1. RSI SIGNALS
    # ===================================================================

    async def _get_rsi_signals(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phát hiện tín hiệu RSI:
        - Vào vùng quá mua (>70) / quá bán (<30)
        - RSI divergence (phân kỳ giá-RSI)
        """
        lookback = kwargs.get("lookback", 20)
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        rsi = RSIIndicator(close=df["close"], window=14)
        df["rsi"] = rsi.rsi()

        signals = []
        scan_df = df.tail(lookback).reset_index(drop=True)

        for i in range(1, len(scan_df)):
            date = scan_df["date"].iloc[i].strftime("%Y-%m-%d")
            rsi_val = scan_df["rsi"].iloc[i]
            rsi_prev = scan_df["rsi"].iloc[i - 1]
            if pd.isna(rsi_val) or pd.isna(rsi_prev):
                continue

            # Vào vùng quá bán
            if rsi_prev >= 30 and rsi_val < 30:
                signals.append({
                    "date": date,
                    "type": "RSI_OVERSOLD_ENTER",
                    "signal": "BUY",
                    "strength": "STRONG" if rsi_val < 20 else "MODERATE",
                    "rsi": self._safe_round(rsi_val),
                    "description": f"RSI vào vùng quá bán ({self._safe_round(rsi_val)})",
                })
            # Ra khỏi quá bán
            elif rsi_prev < 30 and rsi_val >= 30:
                signals.append({
                    "date": date,
                    "type": "RSI_OVERSOLD_EXIT",
                    "signal": "BUY",
                    "strength": "MODERATE",
                    "rsi": self._safe_round(rsi_val),
                    "description": f"RSI thoát vùng quá bán ({self._safe_round(rsi_val)})",
                })
            # Vào vùng quá mua
            elif rsi_prev <= 70 and rsi_val > 70:
                signals.append({
                    "date": date,
                    "type": "RSI_OVERBOUGHT_ENTER",
                    "signal": "SELL",
                    "strength": "STRONG" if rsi_val > 80 else "MODERATE",
                    "rsi": self._safe_round(rsi_val),
                    "description": f"RSI vào vùng quá mua ({self._safe_round(rsi_val)})",
                })
            # Ra khỏi quá mua
            elif rsi_prev > 70 and rsi_val <= 70:
                signals.append({
                    "date": date,
                    "type": "RSI_OVERBOUGHT_EXIT",
                    "signal": "SELL",
                    "strength": "MODERATE",
                    "rsi": self._safe_round(rsi_val),
                    "description": f"RSI thoát vùng quá mua ({self._safe_round(rsi_val)})",
                })

        # Phát hiện RSI Divergence (giá tăng nhưng RSI giảm hoặc ngược lại)
        divergence = self._detect_rsi_divergence(df, lookback)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "signal_type": "RSI",
            "current_rsi": self._safe_round(df["rsi"].iloc[-1]),
            "signals": signals,
            "divergence": divergence,
            "lookback_periods": lookback,
        }

    def _detect_rsi_divergence(self, df: pd.DataFrame, lookback: int = 20) -> Optional[Dict]:
        """Phát hiện phân kỳ giá - RSI."""
        scan = df.tail(lookback)
        if len(scan) < 10:
            return None

        # So sánh nửa đầu vs nửa cuối
        half = len(scan) // 2
        first_half = scan.iloc[:half]
        second_half = scan.iloc[half:]

        price_trend = second_half["close"].mean() - first_half["close"].mean()
        rsi_trend = second_half["rsi"].mean() - first_half["rsi"].mean()

        if pd.isna(price_trend) or pd.isna(rsi_trend):
            return None

        # Bearish divergence: giá tăng, RSI giảm
        if price_trend > 0 and rsi_trend < -2:
            return {
                "type": "BEARISH_DIVERGENCE",
                "signal": "SELL",
                "description": "⚠️ Phân kỳ giảm: Giá tăng nhưng RSI giảm → Sức mua yếu dần",
            }
        # Bullish divergence: giá giảm, RSI tăng
        if price_trend < 0 and rsi_trend > 2:
            return {
                "type": "BULLISH_DIVERGENCE",
                "signal": "BUY",
                "description": "✅ Phân kỳ tăng: Giá giảm nhưng RSI tăng → Sức bán yếu dần",
            }
        return None

    # ===================================================================
    # 2. MACD SIGNALS
    # ===================================================================

    async def _get_macd_signals(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phát hiện MACD crossover:
        - Bullish: MACD cắt lên Signal Line
        - Bearish: MACD cắt xuống Signal Line
        - Zero-line crossover
        """
        lookback = kwargs.get("lookback", 30)
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        macd = MACD(close=df["close"], window_fast=12, window_slow=26, window_sign=9)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        signals = []
        scan_df = df.tail(lookback).reset_index(drop=True)

        for i in range(1, len(scan_df)):
            date = scan_df["date"].iloc[i].strftime("%Y-%m-%d")
            macd_val = scan_df["macd"].iloc[i]
            sig_val = scan_df["macd_signal"].iloc[i]
            prev_macd = scan_df["macd"].iloc[i - 1]
            prev_sig = scan_df["macd_signal"].iloc[i - 1]

            if any(pd.isna(v) for v in [macd_val, sig_val, prev_macd, prev_sig]):
                continue

            # Bullish crossover (MACD cắt lên Signal)
            if prev_macd <= prev_sig and macd_val > sig_val:
                # Crossover xảy ra dưới 0 → mạnh hơn
                strength = "STRONG" if macd_val < 0 else "MODERATE"
                signals.append({
                    "date": date,
                    "type": "MACD_BULLISH_CROSSOVER",
                    "signal": "BUY",
                    "strength": strength,
                    "macd": self._safe_round(macd_val),
                    "macd_signal_line": self._safe_round(sig_val),
                    "description": f"🟢 MACD cắt lên Signal Line",
                })

            # Bearish crossover (MACD cắt xuống Signal)
            elif prev_macd >= prev_sig and macd_val < sig_val:
                strength = "STRONG" if macd_val > 0 else "MODERATE"
                signals.append({
                    "date": date,
                    "type": "MACD_BEARISH_CROSSOVER",
                    "signal": "SELL",
                    "strength": strength,
                    "macd": self._safe_round(macd_val),
                    "macd_signal_line": self._safe_round(sig_val),
                    "description": f"🔴 MACD cắt xuống Signal Line",
                })

            # Zero-line crossover
            if prev_macd <= 0 and macd_val > 0:
                signals.append({
                    "date": date,
                    "type": "MACD_ZERO_BULLISH",
                    "signal": "BUY",
                    "strength": "MODERATE",
                    "macd": self._safe_round(macd_val),
                    "description": "MACD vượt lên trên đường 0",
                })
            elif prev_macd >= 0 and macd_val < 0:
                signals.append({
                    "date": date,
                    "type": "MACD_ZERO_BEARISH",
                    "signal": "SELL",
                    "strength": "MODERATE",
                    "macd": self._safe_round(macd_val),
                    "description": "MACD rơi xuống dưới đường 0",
                })

        return {
            "success": True,
            "symbol": symbol.upper(),
            "signal_type": "MACD",
            "current": {
                "macd": self._safe_round(df["macd"].iloc[-1]),
                "signal": self._safe_round(df["macd_signal"].iloc[-1]),
                "histogram": self._safe_round(df["macd_histogram"].iloc[-1]),
            },
            "signals": signals,
            "lookback_periods": lookback,
        }

    # ===================================================================
    # 3. MA CROSS SIGNALS (Golden Cross / Death Cross)
    # ===================================================================

    async def _get_ma_cross_signals(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phát hiện Golden Cross / Death Cross:
        - Golden Cross: SMA50 cắt lên SMA200 → Bullish dài hạn
        - Death Cross: SMA50 cắt xuống SMA200 → Bearish dài hạn
        - EMA crossovers: EMA9 vs EMA21 (ngắn hạn)
        """
        lookback = kwargs.get("lookback", 30)
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        # SMA 20, 50, 200
        for w in [20, 50, 200]:
            sma = SMAIndicator(close=df["close"], window=w)
            df[f"sma_{w}"] = sma.sma_indicator()

        # EMA 9, 21
        for w in [9, 21]:
            ema = EMAIndicator(close=df["close"], window=w)
            df[f"ema_{w}"] = ema.ema_indicator()

        signals = []
        scan_df = df.tail(lookback).reset_index(drop=True)

        cross_pairs = [
            ("sma_50", "sma_200", "Golden Cross (SMA50/SMA200)", "Death Cross (SMA50/SMA200)", "STRONG"),
            ("sma_20", "sma_50", "SMA20 cắt lên SMA50", "SMA20 cắt xuống SMA50", "MODERATE"),
            ("ema_9", "ema_21", "EMA9 cắt lên EMA21 (ngắn hạn)", "EMA9 cắt xuống EMA21 (ngắn hạn)", "MODERATE"),
        ]

        for short_col, long_col, bull_name, bear_name, strength in cross_pairs:
            for i in range(1, len(scan_df)):
                short_val = scan_df[short_col].iloc[i]
                long_val = scan_df[long_col].iloc[i]
                prev_short = scan_df[short_col].iloc[i - 1]
                prev_long = scan_df[long_col].iloc[i - 1]

                if any(pd.isna(v) for v in [short_val, long_val, prev_short, prev_long]):
                    continue

                date = scan_df["date"].iloc[i].strftime("%Y-%m-%d")

                # Bullish cross
                if prev_short <= prev_long and short_val > long_val:
                    signals.append({
                        "date": date,
                        "type": "GOLDEN_CROSS" if "Golden" in bull_name else "MA_BULLISH_CROSS",
                        "signal": "BUY",
                        "strength": strength,
                        "pairs": f"{short_col} / {long_col}",
                        "description": f"🌟 {bull_name}",
                    })

                # Bearish cross
                elif prev_short >= prev_long and short_val < long_val:
                    signals.append({
                        "date": date,
                        "type": "DEATH_CROSS" if "Death" in bear_name else "MA_BEARISH_CROSS",
                        "signal": "SELL",
                        "strength": strength,
                        "pairs": f"{short_col} / {long_col}",
                        "description": f"💀 {bear_name}",
                    })

        # Trạng thái hiện tại
        current_status = {}
        close_val = df["close"].iloc[-1]
        for col in ["sma_20", "sma_50", "sma_200", "ema_9", "ema_21"]:
            val = df[col].iloc[-1]
            if pd.notna(val):
                current_status[col] = {
                    "value": self._safe_round(val),
                    "price_position": "above" if close_val > val else "below",
                }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "signal_type": "MA_CROSS",
            "close": self._safe_round(close_val),
            "current_ma": current_status,
            "signals": signals,
            "lookback_periods": lookback,
        }

    # ===================================================================
    # 4. SUPPORT / RESISTANCE
    # ===================================================================

    async def _get_support_resistance(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Tính toán vùng hỗ trợ / kháng cự:
        - Pivot Points (Classic)
        - Dựa trên đỉnh/đáy gần đây
        - Bollinger Bands làm S/R động
        """
        lookback = kwargs.get("lookback", 60)
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))
        scan = df.tail(lookback).reset_index(drop=True)

        close = scan["close"].iloc[-1]
        high = scan["high"].iloc[-1]
        low = scan["low"].iloc[-1]

        # --- Classic Pivot Points ---
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)

        pivot_points = {
            "pivot": self._safe_round(pivot),
            "resistance_1": self._safe_round(r1),
            "resistance_2": self._safe_round(r2),
            "resistance_3": self._safe_round(r3),
            "support_1": self._safe_round(s1),
            "support_2": self._safe_round(s2),
            "support_3": self._safe_round(s3),
        }

        # --- Đỉnh / Đáy gần đây (swing highs/lows) ---
        swing_levels = self._find_swing_levels(scan, window=5)

        # --- Bollinger Bands làm S/R động ---
        bb = BollingerBands(close=scan["close"], window=20, window_dev=2)
        dynamic_sr = {
            "bb_upper_resistance": self._safe_round(bb.bollinger_hband().iloc[-1]),
            "bb_middle_support": self._safe_round(bb.bollinger_mavg().iloc[-1]),
            "bb_lower_support": self._safe_round(bb.bollinger_lband().iloc[-1]),
        }

        # --- Đánh giá vị trí giá hiện tại ---
        assessment = self._assess_price_position(close, pivot_points, dynamic_sr)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "signal_type": "SUPPORT_RESISTANCE",
            "close": self._safe_round(close),
            "pivot_points": pivot_points,
            "swing_levels": swing_levels,
            "dynamic_sr": dynamic_sr,
            "assessment": assessment,
        }

    def _find_swing_levels(self, df: pd.DataFrame, window: int = 5) -> Dict[str, List]:
        """Tìm các đỉnh/đáy cục bộ (swing highs / swing lows)."""
        highs = []
        lows = []

        for i in range(window, len(df) - window):
            # Swing high: đỉnh cao hơn N phiên trước và sau
            if df["high"].iloc[i] == df["high"].iloc[i - window: i + window + 1].max():
                highs.append({
                    "date": df["date"].iloc[i].strftime("%Y-%m-%d"),
                    "price": self._safe_round(df["high"].iloc[i]),
                })
            # Swing low: đáy thấp hơn N phiên trước và sau
            if df["low"].iloc[i] == df["low"].iloc[i - window: i + window + 1].min():
                lows.append({
                    "date": df["date"].iloc[i].strftime("%Y-%m-%d"),
                    "price": self._safe_round(df["low"].iloc[i]),
                })

        # Giữ lại tối đa 5 đỉnh/đáy gần nhất
        return {
            "resistance_levels": highs[-5:],
            "support_levels": lows[-5:],
        }

    def _assess_price_position(self, close: float, pivots: Dict, dynamic: Dict) -> str:
        """Đánh giá vị trí giá so với S/R."""
        parts = []
        pivot_val = pivots.get("pivot")
        if pivot_val:
            if close > pivot_val:
                parts.append("Giá trên Pivot → Thiên tăng")
            else:
                parts.append("Giá dưới Pivot → Thiên giảm")

        # Khoảng cách đến S/R gần nhất
        s1 = pivots.get("support_1")
        r1 = pivots.get("resistance_1")
        if s1 and r1 and close:
            dist_s = abs(close - s1) / close * 100
            dist_r = abs(r1 - close) / close * 100
            if dist_s < 1:
                parts.append(f"⚠️ Gần hỗ trợ S1 ({dist_s:.1f}%)")
            if dist_r < 1:
                parts.append(f"⚠️ Gần kháng cự R1 ({dist_r:.1f}%)")

        return " | ".join(parts) if parts else "Giá ở vùng trung tính"

    # ===================================================================
    # 5. TREND DETECTION
    # ===================================================================

    async def _get_trend(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Phát hiện xu hướng:
        - Ngắn hạn (5-20 phiên): EMA9 vs EMA21
        - Trung hạn (20-60 phiên): SMA20 vs SMA50
        - Dài hạn (>60 phiên): SMA50 vs SMA200
        - ADX (Average Directional Index) cho sức mạnh xu hướng
        """
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))

        # Thêm MAs
        for w in [9, 21, 50, 200]:
            ema = EMAIndicator(close=df["close"], window=w)
            df[f"ema_{w}"] = ema.ema_indicator()
        for w in [20, 50, 200]:
            sma = SMAIndicator(close=df["close"], window=w)
            df[f"sma_{w}"] = sma.sma_indicator()

        # ADX cho sức mạnh xu hướng
        try:
            from ta.trend import ADXIndicator
            adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
            df["adx"] = adx.adx()
            df["di_plus"] = adx.adx_pos()
            df["di_minus"] = adx.adx_neg()
            has_adx = True
        except Exception:
            has_adx = False

        close = df["close"].iloc[-1]

        # Xu hướng theo khung thời gian
        trends = {}

        # Ngắn hạn
        ema9 = df["ema_9"].iloc[-1]
        ema21 = df["ema_21"].iloc[-1]
        if pd.notna(ema9) and pd.notna(ema21):
            if ema9 > ema21 and close > ema9:
                trends["short_term"] = {"direction": "UPTREND", "label": "🟢 Tăng"}
            elif ema9 < ema21 and close < ema9:
                trends["short_term"] = {"direction": "DOWNTREND", "label": "🔴 Giảm"}
            else:
                trends["short_term"] = {"direction": "SIDEWAYS", "label": "🟡 Đi ngang"}
            trends["short_term"]["ema9"] = self._safe_round(ema9)
            trends["short_term"]["ema21"] = self._safe_round(ema21)

        # Trung hạn
        sma20 = df["sma_20"].iloc[-1]
        sma50 = df["sma_50"].iloc[-1]
        if pd.notna(sma20) and pd.notna(sma50):
            if sma20 > sma50 and close > sma20:
                trends["medium_term"] = {"direction": "UPTREND", "label": "🟢 Tăng"}
            elif sma20 < sma50 and close < sma20:
                trends["medium_term"] = {"direction": "DOWNTREND", "label": "🔴 Giảm"}
            else:
                trends["medium_term"] = {"direction": "SIDEWAYS", "label": "🟡 Đi ngang"}
            trends["medium_term"]["sma20"] = self._safe_round(sma20)
            trends["medium_term"]["sma50"] = self._safe_round(sma50)

        # Dài hạn
        sma50_val = df["sma_50"].iloc[-1]
        sma200 = df["sma_200"].iloc[-1]
        if pd.notna(sma50_val) and pd.notna(sma200):
            if sma50_val > sma200 and close > sma50_val:
                trends["long_term"] = {"direction": "UPTREND", "label": "🟢 Tăng"}
            elif sma50_val < sma200 and close < sma50_val:
                trends["long_term"] = {"direction": "DOWNTREND", "label": "🔴 Giảm"}
            else:
                trends["long_term"] = {"direction": "SIDEWAYS", "label": "🟡 Đi ngang"}
            trends["long_term"]["sma50"] = self._safe_round(sma50_val)
            trends["long_term"]["sma200"] = self._safe_round(sma200)

        # ADX
        adx_info = None
        if has_adx:
            adx_val = df["adx"].iloc[-1]
            di_plus = df["di_plus"].iloc[-1]
            di_minus = df["di_minus"].iloc[-1]
            if pd.notna(adx_val):
                if adx_val > 25:
                    strength = "Xu hướng mạnh" if adx_val > 40 else "Xu hướng rõ ràng"
                else:
                    strength = "Không có xu hướng rõ / Đi ngang"
                adx_info = {
                    "adx": self._safe_round(adx_val),
                    "di_plus": self._safe_round(di_plus),
                    "di_minus": self._safe_round(di_minus),
                    "strength": strength,
                    "dominant": "Buyers (DI+)" if di_plus > di_minus else "Sellers (DI-)",
                }

        # Tổng hợp
        directions = [t.get("direction") for t in trends.values()]
        if all(d == "UPTREND" for d in directions):
            overall = "🟢 UPTREND tất cả khung → Xu hướng tăng mạnh"
        elif all(d == "DOWNTREND" for d in directions):
            overall = "🔴 DOWNTREND tất cả khung → Xu hướng giảm mạnh"
        elif directions.count("UPTREND") > directions.count("DOWNTREND"):
            overall = "🟢 Thiên tăng (đa số khung tăng)"
        elif directions.count("DOWNTREND") > directions.count("UPTREND"):
            overall = "🔴 Thiên giảm (đa số khung giảm)"
        else:
            overall = "🟡 Hỗn hợp / Đi ngang"

        return {
            "success": True,
            "symbol": symbol.upper(),
            "signal_type": "TREND",
            "close": self._safe_round(close),
            "trends": trends,
            "adx": adx_info,
            "overall": overall,
        }

    # ===================================================================
    # 6. ALL SIGNALS
    # ===================================================================

    async def _get_all_signals(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Tổng hợp tất cả tín hiệu."""
        lookback = kwargs.get("lookback", 20)

        rsi_result = await self._get_rsi_signals(symbol, **kwargs)
        macd_result = await self._get_macd_signals(symbol, **kwargs)
        ma_result = await self._get_ma_cross_signals(symbol, **kwargs)
        sr_result = await self._get_support_resistance(symbol, **kwargs)
        trend_result = await self._get_trend(symbol, **kwargs)

        # Gom tất cả tín hiệu theo ngày
        all_signals = []
        for result in [rsi_result, macd_result, ma_result]:
            if result.get("success"):
                all_signals.extend(result.get("signals", []))

        # Sắp xếp theo ngày
        all_signals.sort(key=lambda x: x.get("date", ""), reverse=True)

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "all_signals",
            "rsi": rsi_result.get("current_rsi") if rsi_result.get("success") else None,
            "trend": trend_result.get("overall") if trend_result.get("success") else None,
            "support_resistance": sr_result.get("pivot_points") if sr_result.get("success") else None,
            "signals": all_signals,
            "total_signals": len(all_signals),
        }

    # ===================================================================
    # 7. RECOMMENDATION (Khuyến nghị tổng hợp)
    # ===================================================================

    async def _get_recommendation(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Khuyến nghị giao dịch dựa trên tổng hợp tất cả tín hiệu.
        Kết hợp: Trend + RSI + MACD + MA + Bollinger + Stochastic + S/R
        """
        df = await self._fetch_price_df(symbol, kwargs.get("start"), kwargs.get("end"))
        df = self._add_indicators(df)
        close = df["close"].iloc[-1]

        factors = []  # (tên, tín hiệu: +1=buy, -1=sell, 0=neutral, trọng số)

        # --- RSI ---
        rsi_val = df["rsi"].iloc[-1]
        if pd.notna(rsi_val):
            if rsi_val < 30:
                factors.append(("RSI quá bán", +1, 2))
            elif rsi_val > 70:
                factors.append(("RSI quá mua", -1, 2))
            elif rsi_val < 40:
                factors.append(("RSI thiên giảm", -0.5, 1))
            elif rsi_val > 60:
                factors.append(("RSI thiên tăng", +0.5, 1))
            else:
                factors.append(("RSI trung tính", 0, 1))

        # --- MACD ---
        macd_val = df["macd"].iloc[-1]
        macd_sig = df["macd_signal"].iloc[-1]
        macd_hist = df["macd_histogram"].iloc[-1]
        if pd.notna(macd_val) and pd.notna(macd_sig):
            if len(df) >= 2:
                prev_macd = df["macd"].iloc[-2]
                prev_sig = df["macd_signal"].iloc[-2]
                if pd.notna(prev_macd) and pd.notna(prev_sig):
                    if prev_macd <= prev_sig and macd_val > macd_sig:
                        factors.append(("MACD bullish crossover", +1, 2))
                    elif prev_macd >= prev_sig and macd_val < macd_sig:
                        factors.append(("MACD bearish crossover", -1, 2))
            if pd.notna(macd_hist):
                if macd_hist > 0:
                    factors.append(("MACD histogram dương", +0.5, 1))
                else:
                    factors.append(("MACD histogram âm", -0.5, 1))

        # --- Bollinger Bands ---
        pband = df["bb_pband"].iloc[-1]
        if pd.notna(pband):
            if pband > 1.0:
                factors.append(("BB quá mua", -1, 1.5))
            elif pband < 0.0:
                factors.append(("BB quá bán", +1, 1.5))
            elif pband > 0.8:
                factors.append(("BB thiên tăng", -0.5, 1))
            elif pband < 0.2:
                factors.append(("BB thiên giảm", +0.5, 1))

        # --- Stochastic ---
        stoch_k = df["stoch_k"].iloc[-1]
        stoch_d = df["stoch_d"].iloc[-1]
        if pd.notna(stoch_k):
            if stoch_k < 20:
                factors.append(("Stochastic quá bán", +1, 1.5))
            elif stoch_k > 80:
                factors.append(("Stochastic quá mua", -1, 1.5))

        # --- Moving Averages ---
        for col, label, weight in [
            ("sma_20", "SMA20", 1), ("sma_50", "SMA50", 1.5), ("sma_200", "SMA200", 2),
        ]:
            ma_val = df[col].iloc[-1]
            if pd.notna(ma_val):
                if close > ma_val:
                    factors.append((f"Giá > {label}", +0.5, weight))
                else:
                    factors.append((f"Giá < {label}", -0.5, weight))

        # --- Golden / Death Cross ---
        sma50 = df["sma_50"].iloc[-1]
        sma200 = df["sma_200"].iloc[-1]
        if pd.notna(sma50) and pd.notna(sma200):
            if sma50 > sma200:
                factors.append(("SMA50 > SMA200 (xu hướng tăng)", +1, 2))
            else:
                factors.append(("SMA50 < SMA200 (xu hướng giảm)", -1, 2))

        # --- Tính điểm ---
        weighted_sum = sum(f[1] * f[2] for f in factors)
        total_weight = sum(f[2] for f in factors)
        score = weighted_sum / total_weight if total_weight > 0 else 0

        # Phân loại
        if score > 0.5:
            action = "STRONG_BUY"
            label = "🟢 MUA MẠNH"
        elif score > 0.2:
            action = "BUY"
            label = "🟢 MUA"
        elif score > -0.2:
            action = "HOLD"
            label = "🟡 GIỮ / THEO DÕI"
        elif score > -0.5:
            action = "SELL"
            label = "🔴 BÁN"
        else:
            action = "STRONG_SELL"
            label = "🔴 BÁN MẠNH"

        # ATR cho stop loss / take profit gợi ý
        atr_val = df["atr"].iloc[-1]
        risk_management = None
        if pd.notna(atr_val) and atr_val > 0:
            risk_management = {
                "atr": self._safe_round(atr_val),
                "suggested_stop_loss": self._safe_round(close - 2 * atr_val),
                "suggested_take_profit": self._safe_round(close + 3 * atr_val),
                "risk_reward_ratio": "1:1.5",
            }

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "recommendation",
            "close": self._safe_round(close),
            "recommendation": {
                "action": action,
                "label": label,
                "score": self._safe_round(score, 2),
                "confidence": self._safe_round(abs(score) / 1.0 * 100, 1),
            },
            "factors": [
                {"factor": f[0], "signal": f[1], "weight": f[2]}
                for f in factors
            ],
            "risk_management": risk_management,
            "disclaimer": "⚠️ Đây chỉ là phân tích kỹ thuật tự động, không phải khuyến nghị đầu tư. "
                          "Hãy kết hợp với phân tích cơ bản và quản lý rủi ro.",
        }
