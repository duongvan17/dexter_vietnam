
from typing import Dict, Optional, List, Tuple
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

    def get_function_schemas(self) -> List[Dict]:
        
        schemas: List[Dict] = []
        for _name, tool in self._tools.items():
            schemas.extend(tool.get_function_schemas())
        return schemas

    def resolve_function_name(self, function_name: str) -> Tuple[Optional[BaseTool], str]:

        if "__" not in function_name:
            return None, ""
        parts = function_name.split("__", 1)
        tool_name, action_name = parts[0], parts[1]
        tool = self.get_tool(tool_name)
        return tool, action_name


def register_all_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:

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
