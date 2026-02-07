"""
Module 12: Reporting - Hệ thống báo cáo tự động

Theo CODING_ROADMAP.md - Module 12:
- generate_stock_report: Báo cáo phân tích 1 cổ phiếu
- generate_daily_report: Báo cáo thị trường ngày
- generate_weekly_report: Báo cáo thị trường tuần
- generate_portfolio_report: Báo cáo danh mục đầu tư
- export_to_file: Export báo cáo ra Markdown/HTML
"""
from dexter_vietnam.tools.base import BaseTool
from dexter_vietnam.tools.vietnam.data.vnstock_connector import VnstockTool
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "data", "reports"
)


class ReportingTool(BaseTool):
    """
    Hệ thống tạo báo cáo phân tích chứng khoán Việt Nam:
    - Báo cáo phân tích cổ phiếu (cơ bản + kỹ thuật + rủi ro)
    - Báo cáo thị trường ngày / tuần
    - Báo cáo danh mục đầu tư
    - Export Markdown / HTML
    """

    def __init__(self, output_dir: Optional[str] = None):
        self._data_tool = VnstockTool()
        self._output_dir = output_dir or DEFAULT_REPORTS_DIR
        os.makedirs(self._output_dir, exist_ok=True)

    def get_name(self) -> str:
        return "reporting"

    def get_description(self) -> str:
        return (
            "Tạo báo cáo phân tích chứng khoán: báo cáo cổ phiếu "
            "(cơ bản + kỹ thuật + rủi ro), báo cáo thị trường ngày/tuần, "
            "báo cáo danh mục. Export Markdown/HTML. "
            "Actions: stock_report, daily_report, weekly_report, "
            "portfolio_report, export."
        )

    async def run(self, action: str = "stock_report", **kwargs) -> Dict[str, Any]:
        """
        Thực thi action.

        Actions:
            stock_report     - Báo cáo phân tích 1 cổ phiếu
            daily_report     - Báo cáo thị trường ngày
            weekly_report    - Báo cáo thị trường tuần
            portfolio_report - Báo cáo danh mục đầu tư
            export           - Export báo cáo ra file
        """
        action_map = {
            "stock_report": self.generate_stock_report,
            "daily_report": self.generate_daily_report,
            "weekly_report": self.generate_weekly_report,
            "portfolio_report": self.generate_portfolio_report,
            "export": self.export_to_file,
        }

        if action not in action_map:
            return {
                "success": False,
                "error": f"Action không hợp lệ: {action}. "
                         f"Sử dụng: {list(action_map.keys())}",
            }

        try:
            return await action_map[action](**kwargs)
        except Exception as e:
            logger.error(f"Reporting action '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": f"Lỗi tạo báo cáo: {str(e)}"}

    # =================================================================
    # STOCK REPORT - Báo cáo phân tích cổ phiếu
    # =================================================================

    async def generate_stock_report(
        self,
        symbol: str = "",
        include_technical: bool = True,
        include_risk: bool = True,
        include_news: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo báo cáo phân tích toàn diện cho 1 cổ phiếu.

        Args:
            symbol: Mã cổ phiếu
            include_technical: Bao gồm phân tích kỹ thuật
            include_risk: Bao gồm đánh giá rủi ro
            include_news: Bao gồm tin tức gần đây
        """
        if not symbol:
            return {"success": False, "error": "Cần cung cấp symbol"}

        symbol = symbol.upper()
        report_sections = []
        data_collected = {}

        report_sections.append(f"# 📊 Báo cáo phân tích: {symbol}")
        report_sections.append(f"*Ngày tạo: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")

        # --- Company overview ---
        try:
            overview = await self._data_tool.get_stock_overview(symbol)
            if overview.get("success"):
                info = overview.get("data", {})
                report_sections.append("## 🏢 Thông tin công ty")
                company_name = info.get("short_name") or info.get("companyName") or info.get("organ_name", symbol)
                exchange = info.get("exchange") or info.get("organ_type_code", "N/A")
                industry = info.get("icb_name3") or info.get("industry", "N/A")
                report_sections.append(f"- **Tên**: {company_name}")
                report_sections.append(f"- **Sàn**: {exchange}")
                report_sections.append(f"- **Ngành**: {industry}\n")
                data_collected["overview"] = info
        except Exception as e:
            logger.warning(f"Overview failed for {symbol}: {e}")

        # --- Financial ratios ---
        try:
            from dexter_vietnam.tools.vietnam.fundamental.ratios import FinancialRatiosTool
            ratios_tool = FinancialRatiosTool()
            ratios_result = await ratios_tool.run(symbol=symbol, action="all")
            if ratios_result.get("success"):
                ratios_data = ratios_result.get("data", {})
                report_sections.append("## 📈 Chỉ số tài chính")

                val = ratios_data.get("valuation", {}).get("ratios", {})
                prof = ratios_data.get("profitability", {}).get("ratios", {})
                liq = ratios_data.get("liquidity", {}).get("ratios", {})
                lev = ratios_data.get("leverage", {}).get("ratios", {})
                per_s = ratios_data.get("per_share", {}).get("ratios", {})

                report_sections.append("### Định giá")
                report_sections.append(f"| Chỉ số | Giá trị |")
                report_sections.append(f"|--------|---------|")
                for k, v in val.items():
                    report_sections.append(f"| {k} | {self._fmt(v)} |")

                report_sections.append("\n### Khả năng sinh lời")
                report_sections.append(f"| Chỉ số | Giá trị |")
                report_sections.append(f"|--------|---------|")
                for k, v in prof.items():
                    report_sections.append(f"| {k} | {self._fmt(v)} |")

                report_sections.append("\n### Thanh khoản & Đòn bẩy")
                report_sections.append(f"| Chỉ số | Giá trị |")
                report_sections.append(f"|--------|---------|")
                for k, v in {**liq, **lev}.items():
                    report_sections.append(f"| {k} | {self._fmt(v)} |")

                if per_s:
                    report_sections.append("\n### Trên mỗi cổ phiếu")
                    report_sections.append(f"| Chỉ số | Giá trị |")
                    report_sections.append(f"|--------|---------|")
                    for k, v in per_s.items():
                        report_sections.append(f"| {k} | {self._fmt(v)} |")

                # Assessments
                assessments = []
                for group_name in ["valuation", "profitability", "liquidity", "leverage"]:
                    group = ratios_data.get(group_name, {})
                    assessment = group.get("assessment", "")
                    if assessment:
                        assessments.append(f"- **{group_name.title()}**: {assessment}")
                if assessments:
                    report_sections.append("\n### Đánh giá")
                    report_sections.extend(assessments)

                report_sections.append("")
                data_collected["ratios"] = ratios_data
        except Exception as e:
            logger.warning(f"Ratios failed for {symbol}: {e}")

        # --- Technical Analysis ---
        if include_technical:
            try:
                from dexter_vietnam.tools.vietnam.technical.indicators import TechnicalIndicatorsTool
                tech_tool = TechnicalIndicatorsTool()
                tech_result = await tech_tool.run(symbol=symbol, action="summary")
                if tech_result.get("success"):
                    tech_data = tech_result.get("data", {})
                    report_sections.append("## 📉 Phân tích kỹ thuật")

                    indicators = tech_data.get("indicators", {})
                    if indicators:
                        report_sections.append("| Chỉ báo | Giá trị | Tín hiệu |")
                        report_sections.append("|---------|---------|-----------|")
                        for ind_name, ind_val in indicators.items():
                            if isinstance(ind_val, dict):
                                value = ind_val.get("value", ind_val.get("latest", "N/A"))
                                signal = ind_val.get("signal", ind_val.get("assessment", ""))
                                report_sections.append(
                                    f"| {ind_name} | {self._fmt(value)} | {signal} |"
                                )
                            else:
                                report_sections.append(
                                    f"| {ind_name} | {self._fmt(ind_val)} | - |"
                                )

                    overall = tech_data.get("overall_signal") or tech_data.get("summary", "")
                    if overall:
                        report_sections.append(f"\n**Tín hiệu tổng hợp**: {overall}")

                    report_sections.append("")
                    data_collected["technical"] = tech_data
            except Exception as e:
                logger.warning(f"Technical analysis failed for {symbol}: {e}")

            # Trading signals
            try:
                from dexter_vietnam.tools.vietnam.technical.signals import TradingSignalsTool
                sig_tool = TradingSignalsTool()
                sig_result = await sig_tool.run(symbol=symbol, action="recommendation")
                if sig_result.get("success"):
                    sig_data = sig_result.get("data", {})
                    recommendation = sig_data.get("recommendation", "")
                    signals_list = sig_data.get("signals", [])
                    if recommendation:
                        report_sections.append(f"### Khuyến nghị: **{recommendation}**")
                    if signals_list:
                        report_sections.append("\n**Tín hiệu giao dịch:**")
                        for sig in signals_list[:5]:
                            desc = sig.get("description", sig.get("signal", ""))
                            sig_type = sig.get("type", "")
                            report_sections.append(f"- [{sig_type}] {desc}")
                    report_sections.append("")
                    data_collected["signals"] = sig_data
            except Exception as e:
                logger.warning(f"Signals failed for {symbol}: {e}")

        # --- Risk Assessment ---
        if include_risk:
            try:
                from dexter_vietnam.tools.vietnam.risk.company_risk import CompanyRiskTool
                risk_tool = CompanyRiskTool()
                risk_result = await risk_tool.run(symbol=symbol, action="assessment")
                if risk_result.get("success"):
                    risk_data = risk_result.get("data", {})
                    report_sections.append("## ⚠️ Đánh giá rủi ro")

                    z_score = risk_data.get("altman_z_score", {})
                    if z_score:
                        score = z_score.get("z_score", "N/A")
                        zone = z_score.get("zone", "N/A")
                        report_sections.append(f"- **Altman Z-Score**: {self._fmt(score)} ({zone})")

                    liq_risk = risk_data.get("liquidity_risk", {})
                    if liq_risk:
                        level = liq_risk.get("overall_risk", liq_risk.get("risk_level", "N/A"))
                        report_sections.append(f"- **Rủi ro thanh khoản**: {level}")

                    vol = risk_data.get("volatility", {})
                    if vol:
                        ann_vol = vol.get("annualized_volatility", "N/A")
                        beta = vol.get("beta", "N/A")
                        max_dd = vol.get("max_drawdown", "N/A")
                        report_sections.append(f"- **Biến động (năm)**: {self._fmt(ann_vol)}")
                        report_sections.append(f"- **Beta**: {self._fmt(beta)}")
                        report_sections.append(f"- **Max Drawdown**: {self._fmt(max_dd)}")

                    report_sections.append("")
                    data_collected["risk"] = risk_data
            except Exception as e:
                logger.warning(f"Risk assessment failed for {symbol}: {e}")

        # --- News ---
        if include_news:
            try:
                from dexter_vietnam.tools.vietnam.news.aggregator import NewsAggregatorTool
                news_tool = NewsAggregatorTool()
                news_result = await news_tool.run(
                    action="stock_news", symbol=symbol, limit=5
                )
                if news_result.get("success"):
                    articles = news_result.get("data", news_result.get("articles", []))
                    if articles:
                        report_sections.append("## 📰 Tin tức gần đây")
                        for art in articles[:5]:
                            title = art.get("title", "")
                            url = art.get("url", "")
                            source = art.get("source", "")
                            if title:
                                report_sections.append(f"- [{title}]({url}) *({source})*")
                        report_sections.append("")
                        data_collected["news"] = articles[:5]
            except Exception as e:
                logger.warning(f"News failed for {symbol}: {e}")

        # Footer
        report_sections.append("---")
        report_sections.append(
            f"*Báo cáo được tạo bởi Dexter Vietnam AI Trading Assistant | "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}*"
        )

        report_md = "\n".join(report_sections)

        return {
            "success": True,
            "symbol": symbol,
            "report_type": "stock_report",
            "report_markdown": report_md,
            "data": data_collected,
            "generated_at": datetime.now().isoformat(),
            "message": f"Đã tạo báo cáo phân tích {symbol}.",
        }

    # =================================================================
    # DAILY REPORT - Báo cáo thị trường ngày
    # =================================================================

    async def generate_daily_report(self, **kwargs) -> Dict[str, Any]:
        """
        Tạo báo cáo tổng quan thị trường ngày.
        Bao gồm: chỉ số chính, top tăng/giảm, ngành, khối ngoại.
        """
        report_sections = []
        data_collected = {}
        today = datetime.now().strftime("%d/%m/%Y")

        report_sections.append(f"# 📋 Báo cáo thị trường ngày {today}")
        report_sections.append(f"*Tạo lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}*\n")

        # Market status
        try:
            from dexter_vietnam.tools.vietnam.market.overview import MarketOverviewTool
            market_tool = MarketOverviewTool()
            market_result = await market_tool.run(action="status")
            if market_result.get("success"):
                market_data = market_result.get("data", {})

                # Indices
                indices = market_data.get("indices", {})
                if indices:
                    report_sections.append("## 📊 Chỉ số chính")
                    report_sections.append("| Chỉ số | Giá trị | Thay đổi | % |")
                    report_sections.append("|--------|---------|----------|---|")
                    for idx_name, idx_data in indices.items():
                        if isinstance(idx_data, dict):
                            close = idx_data.get("close", "N/A")
                            change = idx_data.get("change", 0)
                            pct = idx_data.get("change_pct", 0)
                            sign = "+" if change >= 0 else ""
                            report_sections.append(
                                f"| {idx_name} | {self._fmt(close)} | "
                                f"{sign}{self._fmt(change)} | {sign}{self._fmt(pct)}% |"
                            )
                    report_sections.append("")

                # Top gainers/losers
                for label, key in [("🟢 Top tăng", "top_gainers"), ("🔴 Top giảm", "top_losers")]:
                    items = market_data.get(key, [])
                    if items:
                        report_sections.append(f"### {label}")
                        report_sections.append("| Mã | Giá | % |")
                        report_sections.append("|-----|------|-----|")
                        for item in items[:5]:
                            sym = item.get("symbol", "")
                            price = item.get("close", item.get("price", "N/A"))
                            pct = item.get("change_pct", item.get("pct", 0))
                            sign = "+" if pct >= 0 else ""
                            report_sections.append(
                                f"| {sym} | {self._fmt(price)} | {sign}{self._fmt(pct)}% |"
                            )
                        report_sections.append("")

                data_collected["market"] = market_data
        except Exception as e:
            logger.warning(f"Market status failed: {e}")

        # Sector performance
        try:
            from dexter_vietnam.tools.vietnam.market.overview import MarketOverviewTool
            market_tool = MarketOverviewTool()
            sector_result = await market_tool.run(action="sector")
            if sector_result.get("success"):
                sector_data = sector_result.get("data", {})
                sectors = sector_data.get("sectors", sector_data)
                if sectors and isinstance(sectors, dict):
                    report_sections.append("## 🏭 Hiệu suất ngành")
                    report_sections.append("| Ngành | % thay đổi | Xu hướng |")
                    report_sections.append("|-------|-----------|----------|")
                    for sec_name, sec_info in sectors.items():
                        if isinstance(sec_info, dict):
                            pct = sec_info.get("avg_change_pct", sec_info.get("change_pct", 0))
                            trend = "📈" if pct > 0 else "📉" if pct < 0 else "➡️"
                            sign = "+" if pct > 0 else ""
                            report_sections.append(
                                f"| {sec_name} | {sign}{self._fmt(pct)}% | {trend} |"
                            )
                    report_sections.append("")
                data_collected["sectors"] = sector_data
        except Exception as e:
            logger.warning(f"Sector performance failed: {e}")

        # Foreign flow
        try:
            from dexter_vietnam.tools.vietnam.money_flow.tracker import MoneyFlowTool
            flow_tool = MoneyFlowTool()

            buy_result = await flow_tool.run(action="top_foreign_buy", top_n=5)
            sell_result = await flow_tool.run(action="top_foreign_sell", top_n=5)

            if buy_result.get("success"):
                top_buys = buy_result.get("data", {}).get("top_buying", [])
                if top_buys:
                    report_sections.append("## 💰 Khối ngoại")
                    report_sections.append("### Top mua ròng")
                    report_sections.append("| Mã | Giá trị mua ròng |")
                    report_sections.append("|----|-----------------|")
                    for item in top_buys[:5]:
                        sym = item.get("symbol", "")
                        net = item.get("net_value", item.get("foreign_net", "N/A"))
                        report_sections.append(f"| {sym} | {self._fmt(net)} |")
                    report_sections.append("")
                data_collected["foreign_buy"] = top_buys

            if sell_result.get("success"):
                top_sells = sell_result.get("data", {}).get("top_selling", [])
                if top_sells:
                    report_sections.append("### Top bán ròng")
                    report_sections.append("| Mã | Giá trị bán ròng |")
                    report_sections.append("|----|-----------------|")
                    for item in top_sells[:5]:
                        sym = item.get("symbol", "")
                        net = item.get("net_value", item.get("foreign_net", "N/A"))
                        report_sections.append(f"| {sym} | {self._fmt(net)} |")
                    report_sections.append("")
                data_collected["foreign_sell"] = top_sells
        except Exception as e:
            logger.warning(f"Foreign flow failed: {e}")

        # Footer
        report_sections.append("---")
        report_sections.append(
            "*Báo cáo tự động bởi Dexter Vietnam AI Trading Assistant*"
        )

        report_md = "\n".join(report_sections)

        return {
            "success": True,
            "report_type": "daily_report",
            "date": today,
            "report_markdown": report_md,
            "data": data_collected,
            "generated_at": datetime.now().isoformat(),
            "message": f"Đã tạo báo cáo thị trường ngày {today}.",
        }

    # =================================================================
    # WEEKLY REPORT - Báo cáo thị trường tuần
    # =================================================================

    async def generate_weekly_report(self, **kwargs) -> Dict[str, Any]:
        """
        Tạo báo cáo tổng kết thị trường tuần.
        Bao gồm: biến động tuần, ngành nổi bật, top cổ phiếu.
        """
        report_sections = []
        data_collected = {}
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%d/%m")
        week_end = today.strftime("%d/%m/%Y")

        report_sections.append(f"# 📊 Báo cáo tuần: {week_start} - {week_end}")
        report_sections.append(f"*Tạo lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}*\n")

        # Weekly index performance
        try:
            from dexter_vietnam.tools.vietnam.market.overview import MarketOverviewTool
            market_tool = MarketOverviewTool()
            index_result = await market_tool.run(action="status", period="5d")
            if index_result.get("success"):
                market_data = index_result.get("data", {})
                indices = market_data.get("indices", {})
                if indices:
                    report_sections.append("## 📈 Biến động chỉ số tuần qua")
                    report_sections.append("| Chỉ số | Đóng cửa | Thay đổi tuần |")
                    report_sections.append("|--------|---------|--------------|")
                    for idx_name, idx_data in indices.items():
                        if isinstance(idx_data, dict):
                            close = idx_data.get("close", "N/A")
                            pct = idx_data.get("change_pct", 0)
                            sign = "+" if pct >= 0 else ""
                            report_sections.append(
                                f"| {idx_name} | {self._fmt(close)} | {sign}{self._fmt(pct)}% |"
                            )
                    report_sections.append("")
                data_collected["indices"] = indices
        except Exception as e:
            logger.warning(f"Weekly index failed: {e}")

        # Sector weekly performance
        try:
            sector_result = await market_tool.run(action="sector", period="5d")
            if sector_result.get("success"):
                sector_data = sector_result.get("data", {})
                sectors = sector_data.get("sectors", sector_data)
                if sectors and isinstance(sectors, dict):
                    # Sort by change
                    sorted_sectors = sorted(
                        [(name, info) for name, info in sectors.items() if isinstance(info, dict)],
                        key=lambda x: x[1].get("avg_change_pct", 0),
                        reverse=True,
                    )
                    report_sections.append("## 🏭 Ngành tuần qua (xếp theo hiệu suất)")
                    report_sections.append("| Ngành | % tuần | Xu hướng |")
                    report_sections.append("|-------|--------|----------|")
                    for sec_name, sec_info in sorted_sectors:
                        pct = sec_info.get("avg_change_pct", 0)
                        trend = "📈" if pct > 0.5 else "📉" if pct < -0.5 else "➡️"
                        sign = "+" if pct > 0 else ""
                        report_sections.append(
                            f"| {sec_name} | {sign}{self._fmt(pct)}% | {trend} |"
                        )
                    report_sections.append("")
                data_collected["sectors"] = sector_data
        except Exception as e:
            logger.warning(f"Weekly sector failed: {e}")

        # Top weekly performers (scan a small set)
        try:
            from dexter_vietnam.tools.vietnam.market.overview import MarketOverviewTool
            m_tool = MarketOverviewTool()
            symbols_to_scan = m_tool.TOP_SYMBOLS[:30]
            performers = []

            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")

            for sym in symbols_to_scan:
                try:
                    price_result = await self._data_tool.get_stock_price(
                        symbol=sym, start=start_date, end=end_date
                    )
                    if price_result.get("success") and price_result.get("data"):
                        prices = price_result["data"]
                        if isinstance(prices, list) and len(prices) >= 2:
                            old_close = prices[0].get("close", 0)
                            new_close = prices[-1].get("close", 0)
                            if old_close and old_close > 0:
                                pct = ((new_close - old_close) / old_close) * 100
                                performers.append({
                                    "symbol": sym,
                                    "close": new_close,
                                    "change_pct": round(pct, 2),
                                })
                except Exception:
                    continue

            if performers:
                performers.sort(key=lambda x: x["change_pct"], reverse=True)
                top5 = performers[:5]
                bot5 = performers[-5:]

                report_sections.append("## 🏆 Top tăng tuần")
                report_sections.append("| Mã | Giá | % tuần |")
                report_sections.append("|----|------|--------|")
                for p in top5:
                    sign = "+" if p["change_pct"] >= 0 else ""
                    report_sections.append(
                        f"| {p['symbol']} | {self._fmt(p['close'])} | "
                        f"{sign}{p['change_pct']}% |"
                    )

                report_sections.append("\n## 📉 Top giảm tuần")
                report_sections.append("| Mã | Giá | % tuần |")
                report_sections.append("|----|------|--------|")
                for p in bot5:
                    sign = "+" if p["change_pct"] >= 0 else ""
                    report_sections.append(
                        f"| {p['symbol']} | {self._fmt(p['close'])} | "
                        f"{sign}{p['change_pct']}% |"
                    )
                report_sections.append("")

                data_collected["top_gainers_week"] = top5
                data_collected["top_losers_week"] = bot5
        except Exception as e:
            logger.warning(f"Weekly performers scan failed: {e}")

        # Footer
        report_sections.append("---")
        report_sections.append(
            "*Báo cáo tuần bởi Dexter Vietnam AI Trading Assistant*"
        )

        report_md = "\n".join(report_sections)

        return {
            "success": True,
            "report_type": "weekly_report",
            "week": f"{week_start} - {week_end}",
            "report_markdown": report_md,
            "data": data_collected,
            "generated_at": datetime.now().isoformat(),
            "message": f"Đã tạo báo cáo tuần {week_start} - {week_end}.",
        }

    # =================================================================
    # PORTFOLIO REPORT - Báo cáo danh mục
    # =================================================================

    async def generate_portfolio_report(
        self,
        holdings: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Tạo báo cáo danh mục đầu tư.

        Args:
            holdings: Danh sách holdings
                [{"symbol": "VNM", "quantity": 1000, "avg_price": 75.0}, ...]
        """
        if not holdings:
            return {
                "success": False,
                "error": 'Cần cung cấp holdings: [{"symbol": "VNM", "quantity": 1000, "avg_price": 75.0}]',
            }

        report_sections = []
        data_collected = {}
        today = datetime.now().strftime("%d/%m/%Y")

        report_sections.append(f"# 💼 Báo cáo danh mục đầu tư")
        report_sections.append(f"*Ngày: {today}*\n")

        total_invested = 0
        total_market_value = 0
        portfolio_details = []

        report_sections.append("## 📊 Chi tiết danh mục")
        report_sections.append(
            "| Mã | SL | Giá TB | Giá HT | Giá trị | Lãi/Lỗ | % |"
        )
        report_sections.append(
            "|-----|------|--------|--------|---------|--------|-----|"
        )

        for h in holdings:
            symbol = h.get("symbol", "").upper()
            quantity = h.get("quantity", 0)
            avg_price = h.get("avg_price", 0)

            # Get current price
            current_price = None
            try:
                price_result = await self._data_tool.get_stock_price(symbol=symbol)
                if price_result.get("success") and price_result.get("data"):
                    prices = price_result["data"]
                    if isinstance(prices, list) and len(prices) > 0:
                        current_price = prices[-1].get("close", 0)
            except Exception:
                pass

            if current_price is None:
                current_price = avg_price  # Fallback

            invested = quantity * avg_price * 1000  # VND
            market_val = quantity * current_price * 1000
            pnl = market_val - invested
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

            total_invested += invested
            total_market_value += market_val

            portfolio_details.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "invested": invested,
                "market_value": market_val,
                "pnl": pnl,
                "pnl_pct": round(pnl_pct, 2),
            })

            pnl_sign = "+" if pnl >= 0 else ""
            pct_sign = "+" if pnl_pct >= 0 else ""
            report_sections.append(
                f"| {symbol} | {quantity:,} | {avg_price:,.1f} | "
                f"{current_price:,.1f} | {market_val/1e6:,.1f}M | "
                f"{pnl_sign}{pnl/1e6:,.1f}M | {pct_sign}{pnl_pct:.1f}% |"
            )

        # Summary
        total_pnl = total_market_value - total_invested
        total_pnl_pct = (
            (total_market_value - total_invested) / total_invested * 100
            if total_invested > 0 else 0
        )
        pnl_sign = "+" if total_pnl >= 0 else ""

        report_sections.append("")
        report_sections.append("## 📋 Tổng kết")
        report_sections.append(f"- **Tổng vốn đầu tư**: {total_invested/1e6:,.1f}M VND")
        report_sections.append(f"- **Tổng giá trị hiện tại**: {total_market_value/1e6:,.1f}M VND")
        report_sections.append(
            f"- **Lãi/Lỗ**: {pnl_sign}{total_pnl/1e6:,.1f}M VND "
            f"({pnl_sign}{total_pnl_pct:.1f}%)"
        )
        status_emoji = "🟢" if total_pnl >= 0 else "🔴"
        report_sections.append(f"- **Trạng thái**: {status_emoji} {'Có lãi' if total_pnl >= 0 else 'Đang lỗ'}")

        # Allocation
        report_sections.append("\n## 📊 Phân bổ danh mục")
        report_sections.append("| Mã | Tỷ trọng |")
        report_sections.append("|-----|---------|")
        for d in portfolio_details:
            weight = (d["market_value"] / total_market_value * 100) if total_market_value > 0 else 0
            bar = "█" * int(weight / 5)
            report_sections.append(f"| {d['symbol']} | {bar} {weight:.1f}% |")

        report_sections.append("")
        report_sections.append("---")
        report_sections.append(
            "*Báo cáo danh mục bởi Dexter Vietnam AI Trading Assistant*"
        )

        report_md = "\n".join(report_sections)

        data_collected["holdings"] = portfolio_details
        data_collected["summary"] = {
            "total_invested": total_invested,
            "total_market_value": total_market_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": round(total_pnl_pct, 2),
        }

        return {
            "success": True,
            "report_type": "portfolio_report",
            "report_markdown": report_md,
            "data": data_collected,
            "generated_at": datetime.now().isoformat(),
            "message": "Đã tạo báo cáo danh mục đầu tư.",
        }

    # =================================================================
    # EXPORT - Export báo cáo ra file
    # =================================================================

    async def export_to_file(
        self,
        report_data: Optional[Dict] = None,
        content: str = "",
        filename: Optional[str] = None,
        format: str = "md",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Export báo cáo ra file Markdown hoặc HTML.

        Args:
            report_data: Kết quả từ generate_*_report()
            content: Nội dung markdown trực tiếp (nếu không dùng report_data)
            filename: Tên file (tự sinh nếu không cung cấp)
            format: "md" hoặc "html"
        """
        # Get markdown content
        md_content = content
        if report_data and not md_content:
            md_content = report_data.get("report_markdown", "")
        if not md_content:
            return {"success": False, "error": "Không có nội dung để export"}

        # Generate filename
        if not filename:
            report_type = "report"
            if report_data:
                report_type = report_data.get("report_type", "report")
                symbol = report_data.get("symbol", "")
                if symbol:
                    report_type = f"{report_type}_{symbol}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report_type}_{timestamp}"

        if format == "html":
            output = self._markdown_to_html(md_content)
            filepath = os.path.join(self._output_dir, f"{filename}.html")
        else:
            output = md_content
            filepath = os.path.join(self._output_dir, f"{filename}.md")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output)

            return {
                "success": True,
                "filepath": filepath,
                "format": format,
                "size_bytes": os.path.getsize(filepath),
                "message": f"Đã export báo cáo: {filepath}",
            }
        except Exception as e:
            return {"success": False, "error": f"Lỗi ghi file: {str(e)}"}

    # =================================================================
    # HELPER METHODS
    # =================================================================

    def _fmt(self, value: Any) -> str:
        """Format a value for display."""
        if value is None or value == "N/A":
            return "N/A"
        if isinstance(value, float):
            if abs(value) >= 1e9:
                return f"{value/1e9:,.1f}B"
            if abs(value) >= 1e6:
                return f"{value/1e6:,.1f}M"
            if abs(value) < 1:
                return f"{value:.4f}"
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _markdown_to_html(self, md_content: str) -> str:
        """Convert markdown to basic HTML."""
        html_parts = [
            "<!DOCTYPE html>",
            '<html lang="vi">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>Dexter Vietnam Report</title>",
            "<style>",
            "  body { font-family: 'Segoe UI', Tahoma, sans-serif; ",
            "         max-width: 900px; margin: 40px auto; padding: 0 20px; ",
            "         line-height: 1.6; color: #333; background: #f9fafb; }",
            "  h1 { color: #1a56db; border-bottom: 2px solid #1a56db; padding-bottom: 8px; }",
            "  h2 { color: #1e40af; margin-top: 24px; }",
            "  h3 { color: #374151; }",
            "  table { border-collapse: collapse; width: 100%; margin: 12px 0; }",
            "  th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }",
            "  th { background-color: #e5e7eb; font-weight: 600; }",
            "  tr:nth-child(even) { background-color: #f3f4f6; }",
            "  code { background: #e5e7eb; padding: 2px 6px; border-radius: 4px; }",
            "  strong { color: #111827; }",
            "  hr { border: none; border-top: 1px solid #d1d5db; margin: 24px 0; }",
            "  em { color: #6b7280; }",
            "  ul { padding-left: 20px; }",
            "</style>",
            "</head>",
            "<body>",
        ]

        # Simple markdown → HTML conversion
        lines = md_content.split("\n")
        in_table = False
        in_list = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if in_list:
                    html_parts.append("</ul>")
                    in_list = False
                if in_table:
                    html_parts.append("</table>")
                    in_table = False
                continue

            # Headers
            if stripped.startswith("# "):
                html_parts.append(f"<h1>{self._md_inline(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                html_parts.append(f"<h2>{self._md_inline(stripped[3:])}</h2>")
            elif stripped.startswith("### "):
                html_parts.append(f"<h3>{self._md_inline(stripped[4:])}</h3>")
            # Horizontal rule
            elif stripped == "---":
                html_parts.append("<hr>")
            # Table separator (skip)
            elif stripped.startswith("|") and set(stripped.replace("|", "").replace("-", "").strip()) == set():
                continue
            # Table header/row
            elif stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if not in_table:
                    html_parts.append("<table>")
                    in_table = True
                    html_parts.append("<tr>" + "".join(f"<th>{self._md_inline(c)}</th>" for c in cells) + "</tr>")
                else:
                    html_parts.append("<tr>" + "".join(f"<td>{self._md_inline(c)}</td>" for c in cells) + "</tr>")
            # List item
            elif stripped.startswith("- "):
                if not in_list:
                    html_parts.append("<ul>")
                    in_list = True
                html_parts.append(f"<li>{self._md_inline(stripped[2:])}</li>")
            # Paragraph
            else:
                html_parts.append(f"<p>{self._md_inline(stripped)}</p>")

        if in_table:
            html_parts.append("</table>")
        if in_list:
            html_parts.append("</ul>")

        html_parts.extend(["</body>", "</html>"])
        return "\n".join(html_parts)

    def _md_inline(self, text: str) -> str:
        """Convert inline markdown (bold, italic, links)."""
        import re
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Links
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text
