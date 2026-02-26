"""
Tool Registry - Quản lý và đăng ký tất cả các tools
Đăng ký tự động các tools từ module vietnam/
"""
from typing import Dict, Type, Optional, List
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing all available tools"""

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        name = tool.get_name()
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools"""
        return dict(self._tools)

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        """Get formatted description of all tools for LLM prompt.
        Automatically includes action list from each tool's get_actions()."""
        lines = []
        for name, tool in self._tools.items():
            desc = tool.get_description()
            actions = tool.get_actions()
            action_list = ", ".join(actions.keys())
            lines.append(f"- **{name}**: {desc}")
            lines.append(f"  Actions: {action_list}")
            # Add per-action hints (first 60 chars)
            for action_name, action_desc in actions.items():
                if action_desc:
                    short = action_desc[:80]
                    lines.append(f"    - `{action_name}`: {short}")
        return "\n".join(lines)

    def get_tools_schema(self) -> List[Dict]:
        """Get all tools as JSON schema for LLM function calling."""
        schemas = []
        for name, tool in self._tools.items():
            schemas.append({
                "name": name,
                "description": tool.get_description(),
            })
        return schemas


def register_all_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """
    Discover and register all available tools.
    
    Returns:
        ToolRegistry with all tools registered
    """
    if registry is None:
        registry = ToolRegistry.get_instance()

    tools_registered = []
    tools_failed = []

    # --- Module 1: Data ---
    try:
        from .vietnam.data.vnstock_connector import VnstockTool
        registry.register(VnstockTool())
        tools_registered.append("vnstock_connector")
    except Exception as e:
        tools_failed.append(("vnstock_connector", str(e)))

    # --- Module 2: Fundamental ---
    try:
        from .vietnam.fundamental.financial_statements import FinancialStatementsTool
        registry.register(FinancialStatementsTool())
        tools_registered.append("financial_statements")
    except Exception as e:
        tools_failed.append(("financial_statements", str(e)))

    try:
        from .vietnam.fundamental.ratios import FinancialRatiosTool
        registry.register(FinancialRatiosTool())
        tools_registered.append("financial_ratios")
    except Exception as e:
        tools_failed.append(("financial_ratios", str(e)))

    # --- Module 3: Technical ---
    try:
        from .vietnam.technical.indicators import TechnicalIndicatorsTool
        registry.register(TechnicalIndicatorsTool())
        tools_registered.append("technical_indicators")
    except Exception as e:
        tools_failed.append(("technical_indicators", str(e)))

    try:
        from .vietnam.technical.signals import TradingSignalsTool
        registry.register(TradingSignalsTool())
        tools_registered.append("trading_signals")
    except Exception as e:
        tools_failed.append(("trading_signals", str(e)))

    # --- Module 4: Money Flow ---
    try:
        from .vietnam.money_flow.tracker import MoneyFlowTool
        registry.register(MoneyFlowTool())
        tools_registered.append("money_flow")
    except Exception as e:
        tools_failed.append(("money_flow", str(e)))

    # --- Module 5: News ---
    try:
        from .vietnam.news.aggregator import NewsAggregatorTool
        registry.register(NewsAggregatorTool())
        tools_registered.append("news_aggregator")
    except Exception as e:
        tools_failed.append(("news_aggregator", str(e)))

    try:
        from .vietnam.news.sentiment import SentimentAnalysisTool
        registry.register(SentimentAnalysisTool())
        tools_registered.append("sentiment_analysis")
    except Exception as e:
        tools_failed.append(("sentiment_analysis", str(e)))

    # --- Module 6: Risk ---
    try:
        from .vietnam.risk.company_risk import CompanyRiskTool
        registry.register(CompanyRiskTool())
        tools_registered.append("company_risk")
    except Exception as e:
        tools_failed.append(("company_risk", str(e)))

    # --- Module 7: Screening ---
    try:
        from .vietnam.screening.screener import StockScreenerTool
        registry.register(StockScreenerTool())
        tools_registered.append("stock_screener")
    except Exception as e:
        tools_failed.append(("stock_screener", str(e)))

    # --- Module 10: Market ---
    try:
        from .vietnam.market.overview import MarketOverviewTool
        registry.register(MarketOverviewTool())
        tools_registered.append("market_overview")
    except Exception as e:
        tools_failed.append(("market_overview", str(e)))

    # --- Module 13: Calculators ---
    try:
        from .vietnam.calculators.basic import CalculatorsTool
        registry.register(CalculatorsTool())
        tools_registered.append("calculators")
    except Exception as e:
        tools_failed.append(("calculators", str(e)))

    logger.info(f"Registered {len(tools_registered)} tools: {tools_registered}")
    if tools_failed:
        for name, err in tools_failed:
            logger.warning(f"Failed to register {name}: {err}")

    return registry
