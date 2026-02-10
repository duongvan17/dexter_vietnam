
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from dexter_vietnam.tools.vietnam.fundamental.financial_statements import FinancialStatementsTool
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import math
import pandas as pd


class CompanyRiskTool(BaseTool):

    def __init__(self):
        self._data_tool = VnstockTool()
        self._fs_tool = FinancialStatementsTool()

    def get_name(self) -> str:
        return "company_risk"

    def get_description(self) -> str:
        return (
            "Đánh giá rủi ro: Altman Z-Score, rủi ro thanh khoản, "
            "rủi ro danh mục, biến động giá, Beta."
        )

    async def run(self, symbol: str = "", action: str = "assessment", **kwargs) -> Dict[str, Any]:

        action_map = {
            "assessment": self._overall_assessment,
            "analyze": self._overall_assessment,  # Alias cho assessment
            "evaluate": self._overall_assessment,  # Alias: đánh giá rủi ro
            "all": self._overall_assessment,  # Alias: đánh giá tổng hợp tất cả
            "altman_z": self._altman_z_score,
            "liquidity": self._liquidity_risk,
            "volatility": self._volatility_risk,
            "portfolio": self._portfolio_risk,
        }
        if action not in action_map:
            return {"success": False, "error": f"Action không hợp lệ: {action}"}
        try:
            return await action_map[action](symbol, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}


    def _safe_round(self, val: Any, decimals: int = 4) -> Any:
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            return None
        try:
            return round(float(val), decimals)
        except (TypeError, ValueError):
            return val

    async def _get_ratios_flat(self, symbol: str) -> Dict[str, Any]:
        """Lấy chỉ số tài chính dạng flat dict."""
        result = await self._data_tool.get_financial_ratio(symbol)
        if not result.get("success") or not result.get("data"):
            raise ValueError(f"Không lấy được chỉ số tài chính {symbol}")
        row = result["data"][0]
        flat = {}
        for key, val in row.items():
            if isinstance(key, tuple):
                flat[key[1]] = val
            else:
                flat[key] = val
        return flat

    async def _get_price_df(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """Lấy lịch sử giá."""
        result = await self._data_tool.get_stock_price(symbol, start=start, end=end)
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


    async def _altman_z_score(self, symbol: str, **kwargs) -> Dict[str, Any]:

        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        r = self._safe_round

        # Lấy BCTC
        summary = await self._fs_tool.get_financial_summary(symbol)
        if not summary.get("success"):
            return summary
        data = summary["data"]

        # Lấy chỉ số tài chính bổ sung
        try:
            ratios = await self._get_ratios_flat(symbol)
        except Exception:
            ratios = {}

        # Giá trị cần thiết (tỷ đồng)
        total_assets = data.get("total_assets") or 0
        total_liabilities = data.get("total_liabilities") or 0
        total_equity = data.get("total_equity") or 0
        net_revenue = data.get("net_revenue") or 0
        net_income = data.get("net_income") or 0

        # Working Capital proxy: Current Assets - Current Liabilities
        # Dùng total_equity + long term debt - fixed assets (ước lượng)
        current_assets = total_assets * 0.5  # Ước lượng 50% là tài sản ngắn hạn
        current_liabilities = total_liabilities * 0.4  # Ước lượng 40% nợ ngắn hạn
        working_capital = current_assets - current_liabilities

        # Retained Earnings proxy: dùng equity - vốn điều lệ (ước lượng 60% equity)
        retained_earnings = total_equity * 0.4

        # EBIT proxy: dùng gross profit (nếu có) hoặc net_income * 1.3
        gross_profit = data.get("gross_profit") or (net_income * 1.3 if net_income else 0)

        # Market Cap
        market_cap = ratios.get("Vốn hóa (Tỷ đồng)") or (total_equity * 1.5)

        # Tránh chia 0
        if total_assets == 0:
            return {"success": False, "error": "Total Assets = 0, không tính được Z-Score"}

        # Tính các biến X
        x1 = working_capital / total_assets
        x2 = retained_earnings / total_assets
        x3 = gross_profit / total_assets  # EBIT proxy
        x4 = market_cap / total_liabilities if total_liabilities > 0 else 5.0
        x5 = net_revenue / total_assets

        # Z-Score
        z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        # Đánh giá
        if z_score > 2.99:
            zone = "SAFE"
            label = "🟢 AN TOÀN (Safe Zone)"
            description = "Xác suất phá sản rất thấp. Tình hình tài chính lành mạnh."
        elif z_score >= 1.81:
            zone = "GREY"
            label = "🟡 CẢNH BÁO (Grey Zone)"
            description = "Cần theo dõi. Có dấu hiệu áp lực tài chính nhưng chưa nguy hiểm."
        else:
            zone = "DISTRESS"
            label = "🔴 NGUY HIỂM (Distress Zone)"
            description = "Rủi ro phá sản cao. Tình hình tài chính nghiêm trọng."

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "altman_z_score",
            "z_score": r(z_score, 2),
            "zone": zone,
            "assessment": label,
            "description": description,
            "components": {
                "X1_working_capital_ratio": r(x1),
                "X2_retained_earnings_ratio": r(x2),
                "X3_ebit_ratio": r(x3),
                "X4_market_cap_to_liabilities": r(x4),
                "X5_asset_turnover": r(x5),
            },
            "formula": "Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5",
            "thresholds": {"safe": "> 2.99", "grey": "1.81 - 2.99", "distress": "< 1.81"},
            "note": "Một số giá trị dùng ước lượng từ BCTC tổng hợp. "
                    "Kết quả mang tính tham khảo.",
        }


    async def _liquidity_risk(self, symbol: str, **kwargs) -> Dict[str, Any]:

        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        r = self._safe_round

        # Lấy chỉ số tài chính
        try:
            ratios = await self._get_ratios_flat(symbol)
        except Exception as e:
            return {"success": False, "error": str(e)}

        current_ratio = ratios.get("Chỉ số thanh toán hiện thời")
        quick_ratio = ratios.get("Chỉ số thanh toán nhanh")
        cash_ratio = ratios.get("Chỉ số thanh toán tiền mặt")
        interest_coverage = ratios.get("Khả năng chi trả lãi vay")

        # Đánh giá từng chỉ số
        assessments = []
        risk_score = 0  # 0=thấp, tăng dần = rủi ro cao

        # Current Ratio
        cr_assess = "N/A"
        if current_ratio is not None:
            cr = float(current_ratio)
            if cr >= 2.0:
                cr_assess = "🟢 Tốt (≥2.0)"
            elif cr >= 1.5:
                cr_assess = "🟢 Chấp nhận (1.5-2.0)"
            elif cr >= 1.0:
                cr_assess = "🟡 Cảnh báo (1.0-1.5)"
                risk_score += 1
            else:
                cr_assess = "🔴 Nguy hiểm (<1.0)"
                risk_score += 3

        # Quick Ratio
        qr_assess = "N/A"
        if quick_ratio is not None:
            qr = float(quick_ratio)
            if qr >= 1.0:
                qr_assess = "🟢 Tốt (≥1.0)"
            elif qr >= 0.5:
                qr_assess = "🟡 Cảnh báo (0.5-1.0)"
                risk_score += 1
            else:
                qr_assess = "🔴 Thanh khoản yếu (<0.5)"
                risk_score += 2

        # Cash Ratio
        cash_assess = "N/A"
        if cash_ratio is not None:
            cash = float(cash_ratio)
            if cash >= 0.5:
                cash_assess = "🟢 Dư dả tiền mặt"
            elif cash >= 0.2:
                cash_assess = "🟡 Vừa phải"
            else:
                cash_assess = "🔴 Thiếu tiền mặt"
                risk_score += 1

        # Interest Coverage
        ic_assess = "N/A"
        if interest_coverage is not None:
            ic = float(interest_coverage)
            if ic >= 5:
                ic_assess = "🟢 Rất tốt (≥5x)"
            elif ic >= 2:
                ic_assess = "🟢 Chấp nhận (2-5x)"
            elif ic >= 1:
                ic_assess = "🟡 Áp lực lãi vay (1-2x)"
                risk_score += 2
            else:
                ic_assess = "🔴 Không đủ trả lãi (<1x)"
                risk_score += 3

        # Volume Liquidity
        volume_assess = await self._assess_volume_liquidity(symbol)

        # Tổng hợp
        max_risk = 9
        risk_pct = min(risk_score / max_risk * 100, 100)
        if risk_pct <= 20:
            overall = "🟢 RỦI RO THẤP"
        elif risk_pct <= 50:
            overall = "🟡 RỦI RO TRUNG BÌNH"
        elif risk_pct <= 75:
            overall = "🟠 RỦI RO CAO"
        else:
            overall = "🔴 RỦI RO RẤT CAO"

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "liquidity_risk",
            "financial_liquidity": {
                "current_ratio": {"value": r(current_ratio), "assessment": cr_assess},
                "quick_ratio": {"value": r(quick_ratio), "assessment": qr_assess},
                "cash_ratio": {"value": r(cash_ratio), "assessment": cash_assess},
                "interest_coverage": {"value": r(interest_coverage), "assessment": ic_assess},
            },
            "trading_liquidity": volume_assess,
            "risk_score": {"value": risk_score, "max": max_risk, "percent": r(risk_pct, 1)},
            "overall": overall,
        }

    async def _assess_volume_liquidity(self, symbol: str) -> Dict[str, Any]:
        """Đánh giá thanh khoản giao dịch (volume hàng ngày)."""
        try:
            df = await self._get_price_df(symbol)
            recent = df.tail(20)

            avg_volume = recent["volume"].mean()
            min_volume = recent["volume"].min()
            max_volume = recent["volume"].max()

            # Đánh giá
            if avg_volume >= 1_000_000:
                assess = "🟢 Thanh khoản rất cao (>1M CP/ngày)"
            elif avg_volume >= 500_000:
                assess = "🟢 Thanh khoản tốt (500K-1M)"
            elif avg_volume >= 100_000:
                assess = "🟡 Thanh khoản trung bình (100K-500K)"
            elif avg_volume >= 10_000:
                assess = "🟠 Thanh khoản thấp (10K-100K)"
            else:
                assess = "🔴 Thanh khoản rất thấp (<10K) - Khó mua/bán"

            return {
                "avg_volume_20d": int(avg_volume),
                "min_volume_20d": int(min_volume),
                "max_volume_20d": int(max_volume),
                "assessment": assess,
            }
        except Exception:
            return {"assessment": "Không có dữ liệu volume"}


    async def _volatility_risk(self, symbol: str, **kwargs) -> Dict[str, Any]:

        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        r = self._safe_round
        df = await self._get_price_df(symbol)
        df["daily_return"] = df["close"].pct_change()

        # --- Daily & Annualized Volatility ---
        daily_vol = df["daily_return"].std()
        annual_vol = daily_vol * (252 ** 0.5)  # 252 ngày giao dịch/năm

        vol_assess = ""
        if annual_vol is not None and not math.isnan(annual_vol):
            av = annual_vol * 100
            if av > 50:
                vol_assess = "🔴 Biến động rất cao (>50%)"
            elif av > 35:
                vol_assess = "🟠 Biến động cao (35-50%)"
            elif av > 20:
                vol_assess = "🟡 Biến động trung bình (20-35%)"
            else:
                vol_assess = "🟢 Biến động thấp (<20%)"

        # --- Beta (so với VNINDEX) ---
        beta_result = await self._calculate_beta(symbol, df)

        # --- Maximum Drawdown ---
        cummax = df["close"].cummax()
        drawdown = (df["close"] - cummax) / cummax
        max_drawdown = drawdown.min()
        max_dd_date = df.loc[drawdown.idxmin(), "date"].strftime("%Y-%m-%d") if not drawdown.empty else None

        dd_assess = ""
        if max_drawdown is not None:
            dd_pct = abs(max_drawdown) * 100
            if dd_pct > 50:
                dd_assess = f"🔴 Rất lớn (-{dd_pct:.1f}%)"
            elif dd_pct > 30:
                dd_assess = f"🟠 Lớn (-{dd_pct:.1f}%)"
            elif dd_pct > 15:
                dd_assess = f"🟡 Trung bình (-{dd_pct:.1f}%)"
            else:
                dd_assess = f"🟢 Nhỏ (-{dd_pct:.1f}%)"

        # --- Value at Risk (VaR 95%) ---
        # VaR = mean - 1.645 * std (parametric, 95% confidence)
        mean_return = df["daily_return"].mean()
        var_95 = mean_return - 1.645 * daily_vol if daily_vol else None
        var_95_pct = var_95 * 100 if var_95 is not None else None

        # --- Sharpe Ratio (giả sử risk-free rate 5%/năm) ---
        risk_free_daily = 0.05 / 252
        excess_return = mean_return - risk_free_daily
        sharpe = excess_return / daily_vol if daily_vol and daily_vol > 0 else None
        sharpe_annual = sharpe * (252 ** 0.5) if sharpe is not None else None

        sharpe_assess = ""
        if sharpe_annual is not None:
            if sharpe_annual > 1.5:
                sharpe_assess = "🟢 Xuất sắc (>1.5)"
            elif sharpe_annual > 1.0:
                sharpe_assess = "🟢 Tốt (1.0-1.5)"
            elif sharpe_annual > 0.5:
                sharpe_assess = "🟡 Trung bình (0.5-1.0)"
            else:
                sharpe_assess = "🔴 Kém (<0.5)"

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "volatility_risk",
            "volatility": {
                "daily": r(daily_vol * 100, 2),
                "annualized": r(annual_vol * 100, 2),
                "assessment": vol_assess,
            },
            "beta": beta_result,
            "max_drawdown": {
                "value": r(max_drawdown * 100, 2),
                "date": max_dd_date,
                "assessment": dd_assess,
            },
            "var_95": {
                "daily_pct": r(var_95_pct, 2),
                "description": f"Trong 95% trường hợp, thua lỗ 1 ngày không vượt quá {r(abs(var_95_pct or 0), 2)}%",
            },
            "sharpe_ratio": {
                "annualized": r(sharpe_annual, 2),
                "assessment": sharpe_assess,
            },
            "period": {
                "start": df["date"].iloc[0].strftime("%Y-%m-%d"),
                "end": df["date"].iloc[-1].strftime("%Y-%m-%d"),
                "trading_days": len(df),
            },
        }

    async def _calculate_beta(self, symbol: str, stock_df: pd.DataFrame) -> Dict[str, Any]:
        """Tính Beta so với VNINDEX."""
        try:
            # Lấy dữ liệu VNINDEX cùng khoảng thời gian
            start = stock_df["date"].iloc[0].strftime("%Y-%m-%d")
            end = stock_df["date"].iloc[-1].strftime("%Y-%m-%d")

            index_result = await self._data_tool.get_market_index("VNINDEX", start=start, end=end)
            if not index_result.get("success"):
                return {"value": None, "assessment": "Không lấy được dữ liệu VNINDEX"}

            idx_df = pd.DataFrame(index_result["data"])
            if idx_df.empty:
                return {"value": None, "assessment": "Không có dữ liệu VNINDEX"}

            col_map = {"time": "date"}
            idx_df = idx_df.rename(columns={k: v for k, v in col_map.items() if k in idx_df.columns})
            idx_df["date"] = pd.to_datetime(idx_df["date"])
            idx_df = idx_df.sort_values("date").reset_index(drop=True)
            idx_df["index_return"] = idx_df["close"].pct_change()

            stock_df = stock_df.copy()
            stock_df["stock_return"] = stock_df["close"].pct_change()

            # Merge theo ngày
            merged = pd.merge(
                stock_df[["date", "stock_return"]],
                idx_df[["date", "index_return"]],
                on="date",
                how="inner",
            ).dropna()

            if len(merged) < 20:
                return {"value": None, "assessment": "Không đủ dữ liệu để tính Beta"}

            # Beta = Cov(stock, market) / Var(market)
            cov = merged["stock_return"].cov(merged["index_return"])
            var_market = merged["index_return"].var()
            beta = cov / var_market if var_market > 0 else None

            if beta is None:
                return {"value": None, "assessment": "N/A"}

            beta_val = round(beta, 2)
            if beta_val > 1.5:
                assess = f"🔴 Rất nhạy cảm (β={beta_val}) - Biến động mạnh hơn thị trường 50%+"
            elif beta_val > 1.0:
                assess = f"🟠 Nhạy cảm (β={beta_val}) - Biến động hơn thị trường"
            elif beta_val > 0.7:
                assess = f"🟢 Trung bình (β={beta_val}) - Tương đương thị trường"
            elif beta_val > 0:
                assess = f"🟢 Phòng thủ (β={beta_val}) - Ít biến động hơn thị trường"
            else:
                assess = f"⚪ Ngược chiều (β={beta_val})"

            return {"value": beta_val, "assessment": assess}

        except Exception as e:
            return {"value": None, "assessment": f"Lỗi tính Beta: {str(e)}"}


    async def _portfolio_risk(self, symbol: str = "", **kwargs) -> Dict[str, Any]:

        holdings = kwargs.get("holdings", [])
        if not holdings:
            return {"success": False, "error": "Cần cung cấp danh mục: holdings=[{symbol, weight}, ...]"}

        r = self._safe_round

        # Chuẩn hoá weights
        total_weight = sum(h.get("weight", 0) for h in holdings)
        if total_weight == 0:
            return {"success": False, "error": "Tổng weight = 0"}
        for h in holdings:
            h["weight"] = h["weight"] / total_weight

        # Lấy dữ liệu giá cho từng mã
        returns_dict = {}
        failed = []
        for h in holdings:
            sym = h["symbol"]
            try:
                df = await self._get_price_df(sym)
                df["daily_return"] = df["close"].pct_change()
                returns_dict[sym] = df.set_index("date")["daily_return"]
            except Exception:
                failed.append(sym)

        if len(returns_dict) < 2:
            return {
                "success": False,
                "error": f"Cần ít nhất 2 mã có dữ liệu. Lỗi: {failed}",
            }

        # Tạo DataFrame returns
        returns_df = pd.DataFrame(returns_dict).dropna()

        if len(returns_df) < 20:
            return {"success": False, "error": "Không đủ dữ liệu chung giữa các mã"}

        # Weights vector
        symbols_with_data = list(returns_dict.keys())
        weights = [
            next((h["weight"] for h in holdings if h["symbol"] == sym), 0)
            for sym in symbols_with_data
        ]
        # Re-normalize
        w_sum = sum(weights)
        weights = [w / w_sum for w in weights]

        import numpy as np
        w = np.array(weights)

        # Correlation Matrix
        corr_matrix = returns_df.corr()

        # Covariance Matrix
        cov_matrix = returns_df.cov()

        # Portfolio Variance & Volatility
        port_variance = float(w @ cov_matrix.values @ w)
        port_vol_daily = port_variance ** 0.5
        port_vol_annual = port_vol_daily * (252 ** 0.5)

        # Portfolio Expected Return
        mean_returns = returns_df.mean()
        port_return_daily = float(w @ mean_returns.values)
        port_return_annual = port_return_daily * 252

        # Sharpe Ratio (risk-free = 5%/năm)
        risk_free = 0.05
        sharpe = (port_return_annual - risk_free) / port_vol_annual if port_vol_annual > 0 else None

        # Concentration (Herfindahl Index)
        hhi = sum(wi ** 2 for wi in weights)
        if hhi > 0.5:
            concentration = "🔴 Tập trung cao (HHI > 0.5)"
        elif hhi > 0.25:
            concentration = "🟡 Tập trung vừa (HHI 0.25-0.5)"
        else:
            concentration = "🟢 Đa dạng hoá tốt (HHI < 0.25)"

        # Diversification Ratio
        individual_vols = returns_df.std().values
        weighted_avg_vol = float(w @ individual_vols)
        diversification_ratio = weighted_avg_vol / port_vol_daily if port_vol_daily > 0 else None
        # DR > 1 → Đa dạng hoá đang giảm rủi ro

        # Correlation insights
        corr_pairs = []
        for i in range(len(symbols_with_data)):
            for j in range(i + 1, len(symbols_with_data)):
                corr_val = corr_matrix.iloc[i, j]
                corr_pairs.append({
                    "pair": f"{symbols_with_data[i]}-{symbols_with_data[j]}",
                    "correlation": r(corr_val, 2),
                    "note": (
                        "Tương quan cao → ít đa dạng hoá" if corr_val > 0.7
                        else "Tương quan thấp → đa dạng hoá tốt" if corr_val < 0.3
                        else "Tương quan vừa"
                    ),
                })

        # Đánh giá tổng thể
        if port_vol_annual * 100 > 40:
            risk_label = "🔴 RỦI RO CAO"
        elif port_vol_annual * 100 > 25:
            risk_label = "🟡 RỦI RO TRUNG BÌNH"
        else:
            risk_label = "🟢 RỦI RO THẤP"

        return {
            "success": True,
            "report": "portfolio_risk",
            "holdings": [
                {"symbol": sym, "weight": r(w_val * 100, 1)}
                for sym, w_val in zip(symbols_with_data, weights)
            ],
            "failed_symbols": failed,
            "portfolio_metrics": {
                "expected_return_annual": r(port_return_annual * 100, 2),
                "volatility_annual": r(port_vol_annual * 100, 2),
                "sharpe_ratio": r(sharpe, 2),
                "var_95_daily": r((port_return_daily - 1.645 * port_vol_daily) * 100, 2),
            },
            "diversification": {
                "hhi": r(hhi, 3),
                "concentration": concentration,
                "diversification_ratio": r(diversification_ratio, 2),
                "correlation_pairs": corr_pairs,
            },
            "overall": risk_label,
        }


    async def _overall_assessment(self, symbol: str, **kwargs) -> Dict[str, Any]:

        if not symbol:
            return {"success": False, "error": "Cần cung cấp mã cổ phiếu (symbol)"}

        r = self._safe_round

        # Chạy tất cả đánh giá
        results = {}
        risk_points = 0  # Càng cao = càng rủi ro
        max_points = 0

        # Z-Score
        z_result = await self._altman_z_score(symbol)
        results["altman_z"] = z_result
        if z_result.get("success"):
            zone = z_result.get("zone", "")
            if zone == "SAFE":
                risk_points += 0
            elif zone == "GREY":
                risk_points += 2
            else:
                risk_points += 4
            max_points += 4

        # Liquidity
        liq_result = await self._liquidity_risk(symbol)
        results["liquidity"] = liq_result
        if liq_result.get("success"):
            liq_score = liq_result.get("risk_score", {}).get("value", 0)
            risk_points += min(liq_score, 4)
            max_points += 4

        # Volatility
        vol_result = await self._volatility_risk(symbol)
        results["volatility"] = vol_result
        if vol_result.get("success"):
            annual_vol = vol_result.get("volatility", {}).get("annualized")
            if annual_vol is not None:
                if annual_vol > 50:
                    risk_points += 4
                elif annual_vol > 35:
                    risk_points += 3
                elif annual_vol > 20:
                    risk_points += 1
            max_points += 4

            # Beta
            beta = vol_result.get("beta", {}).get("value")
            if beta is not None:
                if beta > 1.5:
                    risk_points += 2
                elif beta > 1.0:
                    risk_points += 1
            max_points += 2

        # Tổng hợp
        risk_pct = risk_points / max_points * 100 if max_points > 0 else 50

        if risk_pct <= 20:
            grade = "A"
            label = "🟢 RỦI RO THẤP"
            advice = "Cổ phiếu có độ an toàn cao. Phù hợp cho nhà đầu tư thận trọng."
        elif risk_pct <= 40:
            grade = "B"
            label = "🟢 RỦI RO TRUNG BÌNH THẤP"
            advice = "Rủi ro ở mức chấp nhận. Cân nhắc tỷ trọng phù hợp."
        elif risk_pct <= 60:
            grade = "C"
            label = "🟡 RỦI RO TRUNG BÌNH"
            advice = "Cần theo dõi kỹ. Đặt stop-loss và quản lý vị thế."
        elif risk_pct <= 80:
            grade = "D"
            label = "🟠 RỦI RO CAO"
            advice = "Cổ phiếu có nhiều rủi ro. Chỉ nên đầu tư tỷ trọng nhỏ."
        else:
            grade = "F"
            label = "🔴 RỦI RO RẤT CAO"
            advice = "Cảnh báo! Cổ phiếu rủi ro rất cao. Cân nhắc kỹ trước khi đầu tư."

        return {
            "success": True,
            "symbol": symbol.upper(),
            "report": "risk_assessment",
            "overall": {
                "grade": grade,
                "label": label,
                "risk_score": r(risk_pct, 1),
                "risk_points": f"{risk_points}/{max_points}",
                "advice": advice,
            },
            "details": {
                "altman_z": {
                    "score": z_result.get("z_score") if z_result.get("success") else None,
                    "zone": z_result.get("assessment") if z_result.get("success") else "N/A",
                },
                "liquidity": {
                    "overall": liq_result.get("overall") if liq_result.get("success") else "N/A",
                },
                "volatility": {
                    "annual": vol_result.get("volatility", {}).get("annualized") if vol_result.get("success") else None,
                    "beta": vol_result.get("beta", {}).get("value") if vol_result.get("success") else None,
                    "max_drawdown": vol_result.get("max_drawdown", {}).get("value") if vol_result.get("success") else None,
                    "sharpe": vol_result.get("sharpe_ratio", {}).get("annualized") if vol_result.get("success") else None,
                },
            },
        }
