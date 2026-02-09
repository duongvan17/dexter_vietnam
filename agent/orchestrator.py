"""
Agent Orchestrator - Trung tâm điều phối AI Agent
Flow: User Query → Planner → Executor → Synthesizer → Response

Theo CODING_ROADMAP.md - Agent Core System
"""
import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from dexter_vietnam.model.llm import LLMWrapper
from dexter_vietnam.tools.registry import ToolRegistry, register_all_tools

logger = logging.getLogger(__name__)


# =====================================================================
# System Prompts
# =====================================================================

SYSTEM_PROMPT = """Bạn là Dexter — Trợ lý AI phân tích chứng khoán Việt Nam.

Bạn có quyền truy cập các công cụ phân tích thị trường chứng khoán Việt Nam.
Nhiệm vụ: Hiểu câu hỏi → Lập kế hoạch tool calls → Phân tích kết quả → Trả lời tiếng Việt rõ ràng.

Nguyên tắc:
- Trả lời bằng tiếng Việt, chuyên nghiệp, dễ hiểu
- Đưa ra nhận định dựa trên dữ liệu thực
- Cảnh báo rủi ro khi cần
- Không tư vấn đầu tư trực tiếp, chỉ phân tích thông tin
- Nếu không có đủ dữ liệu, nói rõ giới hạn
"""

PLANNER_PROMPT = """Bạn là Planner của AI Trading Assistant cho chứng khoán Việt Nam.

Nhiệm vụ: Phân tích câu hỏi người dùng và lập kế hoạch sử dụng tools.

## Các tool có sẵn:
{tools_description}

## Quy tắc:
1. Phân tích ý định câu hỏi
2. Chọn tools phù hợp và parameters cần thiết
3. Xác định thứ tự thực thi (song song nếu được)
4. Trả về JSON plan

## Output format (JSON):
{{
    "intent": "mô tả ngắn ý định",
    "symbols": ["VNM", "FPT"],
    "steps": [
        {{
            "step": 1,
            "tool": "tool_name",
            "action": "action_name",
            "params": {{"symbol": "VNM", "key": "value"}},
            "reason": "Lý do dùng tool này",
            "parallel_group": 1
        }}
    ]
}}

Các step có cùng `parallel_group` sẽ được chạy song song.

## Ví dụ mapping:
- "Phân tích VNM" → financial_ratios(all) + technical_indicators(summary) + trading_signals(recommendation) + company_risk(assessment)
- "Khối ngoại mua gì?" → money_flow(top_foreign_buy)
- "Tin tức FPT" → news_aggregator(stock_news) + sentiment_analysis(stock_sentiment)
- "Lọc cổ phiếu giá trị" → stock_screener(value)
- "Thị trường hôm nay thế nào?" → market_overview(summary)
- "Định giá VCB" → dcf_valuation(valuation)
- "So sánh VNM và VCB" → financial_ratios(all) x2 song song
- "RSI FPT" → technical_indicators(rsi, symbol=FPT)
- "Cảnh báo khi VNM vượt 80" → alerts(create_price, symbol=VNM, target_price=80, condition=above)
- "Xem danh sách cảnh báo" → alerts(list)
- "Kiểm tra cảnh báo" → alerts(check)

Câu hỏi: {query}
"""

SYNTHESIZER_PROMPT = """Bạn là AI phân tích chứng khoán Việt Nam.

Dựa trên dữ liệu từ các công cụ phân tích, hãy tổng hợp câu trả lời bằng tiếng Việt.

## Câu hỏi gốc:
{query}

## Dữ liệu phân tích:
{results}

## Yêu cầu:
- Trả lời bằng tiếng Việt, chuyên nghiệp
- Tóm tắt các điểm chính, dùng số liệu cụ thể
- Đưa ra nhận định/khuyến nghị dựa trên dữ liệu
- Nêu rõ rủi ro nếu có
- Format đẹp với markdown: headings, bullets, bold
- Kết luận ngắn gọn ở cuối
- Nếu có lỗi dữ liệu, vẫn trả lời phần có dữ liệu tốt
"""


# =====================================================================
# Memory - Lưu conversation history
# =====================================================================

class ConversationMemory:
    """Simple conversation memory for context retention."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        # Trim oldest turns
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_context(self, last_n: int = 5) -> str:
        """Get recent conversation as context string."""
        recent = self.history[-last_n * 2:]  # last N turns (user + assistant)
        if not recent:
            return ""
        lines = []
        for turn in recent:
            prefix = "User" if turn["role"] == "user" else "Dexter"
            # Truncate long contents
            content = turn["content"][:500]
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def clear(self) -> None:
        self.history = []


# =====================================================================
# Planner
# =====================================================================

class Planner:
    """Phân tích query → Lập kế hoạch tools cần gọi."""

    def __init__(self, llm: LLMWrapper, registry: ToolRegistry):
        self.llm = llm
        self.registry = registry

    async def create_plan(
        self, query: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze user query and create execution plan.

        Returns:
            {
                "intent": str,
                "symbols": [str],
                "steps": [{"step", "tool", "action", "params", "reason", "parallel_group"}]
            }
        """
        tools_desc = self.registry.get_tools_description()

        prompt = PLANNER_PROMPT.format(
            tools_description=tools_desc,
            query=query,
        )

        if context:
            prompt += f"\n\n## Ngữ cảnh hội thoại trước:\n{context}"

        plan = await self.llm.generate_json(prompt)

        # Validate plan
        if "parse_error" in plan:
            # Fallback: simple keyword matching
            logger.warning("LLM plan parsing failed, using fallback planner")
            plan = self._fallback_plan(query)

        return plan

    def _fallback_plan(self, query: str) -> Dict[str, Any]:
        """
        Fallback planner using keyword matching.
        Used when LLM fails to generate a valid plan.
        """
        query_lower = query.lower()
        steps = []
        symbols = []

        # Extract symbols (uppercase 3-letter codes)
        import re
        found_symbols = re.findall(r'\b([A-Z]{3})\b', query)
        # Filter common Vietnamese words that happen to be 3 uppercase 
        stop_words = {"VND", "USD", "GDP", "CPI", "ETF", "IPO", "CEO", "CFO"}
        symbols = [s for s in found_symbols if s not in stop_words]

        symbol = symbols[0] if symbols else ""
        group = 1

        # Keyword → tool mapping
        if any(k in query_lower for k in ["phân tích", "đánh giá", "review", "analyze"]):
            if symbol:
                steps = [
                    {"step": 1, "tool": "financial_ratios", "action": "all",
                     "params": {"symbol": symbol}, "reason": "Chỉ số tài chính", "parallel_group": 1},
                    {"step": 2, "tool": "technical_indicators", "action": "summary",
                     "params": {"symbol": symbol}, "reason": "Chỉ báo kỹ thuật", "parallel_group": 1},
                    {"step": 3, "tool": "trading_signals", "action": "recommendation",
                     "params": {"symbol": symbol}, "reason": "Tín hiệu giao dịch", "parallel_group": 1},
                    {"step": 4, "tool": "company_risk", "action": "assessment",
                     "params": {"symbol": symbol}, "reason": "Đánh giá rủi ro", "parallel_group": 1},
                ]
            else:
                steps = [
                    {"step": 1, "tool": "market_overview", "action": "summary",
                     "params": {}, "reason": "Tổng quan thị trường", "parallel_group": 1},
                ]

        elif any(k in query_lower for k in ["khối ngoại", "foreign"]):
            if "mua" in query_lower:
                steps = [{"step": 1, "tool": "money_flow", "action": "top_foreign_buy",
                          "params": {}, "reason": "Top mua ròng khối ngoại", "parallel_group": 1}]
            elif "bán" in query_lower:
                steps = [{"step": 1, "tool": "money_flow", "action": "top_foreign_sell",
                          "params": {}, "reason": "Top bán ròng khối ngoại", "parallel_group": 1}]
            else:
                steps = [
                    {"step": 1, "tool": "money_flow", "action": "top_foreign_buy",
                     "params": {}, "reason": "Top mua ròng", "parallel_group": 1},
                    {"step": 2, "tool": "money_flow", "action": "top_foreign_sell",
                     "params": {}, "reason": "Top bán ròng", "parallel_group": 1},
                ]

        elif any(k in query_lower for k in ["tin tức", "news", "tin"]):
            steps = [{"step": 1, "tool": "news_aggregator",
                      "action": "stock_news" if symbol else "market",
                      "params": {"symbol": symbol} if symbol else {},
                      "reason": "Lấy tin tức", "parallel_group": 1}]

        elif any(k in query_lower for k in ["lọc", "sàng lọc", "screen", "tìm"]):
            action = "value"
            if "tăng trưởng" in query_lower or "growth" in query_lower:
                action = "growth"
            elif "oversold" in query_lower or "quá bán" in query_lower:
                action = "oversold"
            steps = [{"step": 1, "tool": "stock_screener", "action": action,
                      "params": {}, "reason": "Sàng lọc cổ phiếu", "parallel_group": 1}]

        elif any(k in query_lower for k in ["thị trường", "market", "vnindex"]):
            steps = [{"step": 1, "tool": "market_overview", "action": "summary",
                      "params": {}, "reason": "Tổng quan thị trường", "parallel_group": 1}]

        elif any(k in query_lower for k in ["định giá", "dcf", "valuation"]):
            if symbol:
                steps = [{"step": 1, "tool": "dcf_valuation", "action": "valuation",
                          "params": {"symbol": symbol}, "reason": "Định giá DCF", "parallel_group": 1}]

        elif any(k in query_lower for k in ["rsi", "macd", "bollinger", "kỹ thuật", "technical"]):
            if symbol:
                steps = [{"step": 1, "tool": "technical_indicators", "action": "all",
                          "params": {"symbol": symbol}, "reason": "Chỉ báo kỹ thuật", "parallel_group": 1}]

        elif any(k in query_lower for k in ["rủi ro", "risk"]):
            if symbol:
                steps = [{"step": 1, "tool": "company_risk", "action": "assessment",
                          "params": {"symbol": symbol}, "reason": "Đánh giá rủi ro", "parallel_group": 1}]

        elif any(k in query_lower for k in ["dòng tiền", "money flow"]):
            if symbol:
                steps = [{"step": 1, "tool": "money_flow", "action": "flow_analysis",
                          "params": {"symbol": symbol}, "reason": "Phân tích dòng tiền", "parallel_group": 1}]

        elif any(k in query_lower for k in ["tài chính", "financial"]):
            if symbol:
                steps = [{"step": 1, "tool": "financial_statements", "action": "summary",
                          "params": {"symbol": symbol}, "reason": "Báo cáo tài chính", "parallel_group": 1}]

        elif any(k in query_lower for k in ["báo cáo", "report"]):
            if "tuần" in query_lower or "weekly" in query_lower:
                steps = [{"step": 1, "tool": "reporting", "action": "weekly_report",
                          "params": {}, "reason": "Báo cáo tuần", "parallel_group": 1}]
            elif "danh mục" in query_lower or "portfolio" in query_lower:
                steps = [{"step": 1, "tool": "reporting", "action": "portfolio_report",
                          "params": {}, "reason": "Báo cáo danh mục", "parallel_group": 1}]
            elif symbol:
                steps = [{"step": 1, "tool": "reporting", "action": "stock_report",
                          "params": {"symbol": symbol}, "reason": "Báo cáo cổ phiếu", "parallel_group": 1}]
            else:
                steps = [{"step": 1, "tool": "reporting", "action": "daily_report",
                          "params": {}, "reason": "Báo cáo ngày", "parallel_group": 1}]

        elif any(k in query_lower for k in [
            "tính", "calculator", "lãi kép", "compound", "position size",
            "khối lượng lệnh", "thuế", "tax", "hoà vốn", "hòa vốn",
            "breakeven", "margin", "ký quỹ", "dca",
        ]):
            if "lãi kép" in query_lower or "compound" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "compound_interest",
                          "params": {}, "reason": "Tính lãi kép", "parallel_group": 1}]
            elif "position" in query_lower or "khối lượng lệnh" in query_lower or "vào lệnh" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "position_sizing",
                          "params": {}, "reason": "Tính khối lượng vào lệnh", "parallel_group": 1}]
            elif "thuế" in query_lower or "tax" in query_lower or "phí" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "tax",
                          "params": {}, "reason": "Tính thuế & phí", "parallel_group": 1}]
            elif "hoà vốn" in query_lower or "hòa vốn" in query_lower or "breakeven" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "breakeven",
                          "params": {}, "reason": "Tính giá hoà vốn", "parallel_group": 1}]
            elif "margin" in query_lower or "ký quỹ" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "margin",
                          "params": {}, "reason": "Tính margin", "parallel_group": 1}]
            elif "dca" in query_lower:
                steps = [{"step": 1, "tool": "calculators", "action": "dca",
                          "params": {}, "reason": "Tính DCA", "parallel_group": 1}]
            else:
                steps = [{"step": 1, "tool": "calculators", "action": "compound_interest",
                          "params": {}, "reason": "Máy tính tài chính", "parallel_group": 1}]

        elif any(k in query_lower for k in [
            "thuật ngữ", "giải thích", "nghĩa là gì", "là gì",
            "hướng dẫn", "tutorial", "học", "kiến thức",
            "case study", "quiz", "kiểm tra", "education",
            "người mới", "newbie", "beginner",
        ]):
            if any(k in query_lower for k in ["quiz", "kiểm tra", "trắc nghiệm"]):
                topic = "all"
                if "cơ bản" in query_lower or "fundamental" in query_lower:
                    topic = "fundamental"
                elif "kỹ thuật" in query_lower or "technical" in query_lower:
                    topic = "technical"
                elif "giao dịch" in query_lower or "trading" in query_lower:
                    topic = "trading"
                steps = [{"step": 1, "tool": "education", "action": "quiz",
                          "params": {"topic": topic}, "reason": "Quiz kiến thức", "parallel_group": 1}]
            elif any(k in query_lower for k in ["hướng dẫn", "tutorial", "học", "người mới", "newbie", "beginner"]):
                topic = "beginner"
                if "cơ bản" in query_lower or "fundamental" in query_lower:
                    topic = "fundamental_analysis"
                elif "kỹ thuật" in query_lower or "technical" in query_lower:
                    topic = "technical_analysis"
                elif "rủi ro" in query_lower or "risk" in query_lower:
                    topic = "risk_management"
                elif "giá trị" in query_lower or "value" in query_lower:
                    topic = "value_investing"
                elif "swing" in query_lower:
                    topic = "swing_trading"
                elif "dca" in query_lower:
                    topic = "dca"
                elif "bctc" in query_lower or "báo cáo tài chính" in query_lower:
                    topic = "reading_financial_statements"
                steps = [{"step": 1, "tool": "education", "action": "tutorial",
                          "params": {"topic": topic}, "reason": "Hướng dẫn", "parallel_group": 1}]
            elif "case study" in query_lower:
                steps = [{"step": 1, "tool": "education", "action": "case_study",
                          "params": {"symbol": symbol} if symbol else {},
                          "reason": "Case study", "parallel_group": 1}]
            elif any(k in query_lower for k in ["danh sách", "list", "liệt kê"]):
                steps = [{"step": 1, "tool": "education", "action": "list_terms",
                          "params": {}, "reason": "Liệt kê thuật ngữ", "parallel_group": 1}]
            else:
                # Extract the term being asked about
                term = query.strip()
                for prefix in ["là gì", "nghĩa là gì", "giải thích", "thuật ngữ"]:
                    term = term.lower().replace(prefix, "").strip().strip("?")
                steps = [{"step": 1, "tool": "education", "action": "define",
                          "params": {"term": term}, "reason": "Giải thích thuật ngữ", "parallel_group": 1}]

        elif any(k in query_lower for k in [
            "danh mục", "portfolio", "watchlist", "theo dõi",
            "xếp hạng", "leaderboard", "top danh mục", "cộng đồng",
        ]):
            if any(k in query_lower for k in ["tạo", "create", "mở"]):
                steps = [{"step": 1, "tool": "social", "action": "create_portfolio",
                          "params": {}, "reason": "Tạo danh mục", "parallel_group": 1}]
            elif any(k in query_lower for k in ["xếp hạng", "leaderboard", "ranking"]):
                steps = [{"step": 1, "tool": "social", "action": "leaderboard",
                          "params": {}, "reason": "Bảng xếp hạng", "parallel_group": 1}]
            elif any(k in query_lower for k in ["top", "hiệu quả", "tốt nhất"]):
                steps = [{"step": 1, "tool": "social", "action": "top_portfolios",
                          "params": {}, "reason": "Top danh mục", "parallel_group": 1}]
            elif any(k in query_lower for k in ["watchlist", "theo dõi"]):
                if any(k in query_lower for k in ["thêm", "add"]):
                    steps = [{"step": 1, "tool": "social", "action": "add_watchlist",
                              "params": {"symbol": symbol} if symbol else {},
                              "reason": "Thêm watchlist", "parallel_group": 1}]
                elif any(k in query_lower for k in ["xoá", "xóa", "remove", "bỏ"]):
                    steps = [{"step": 1, "tool": "social", "action": "remove_watchlist",
                              "params": {"symbol": symbol} if symbol else {},
                              "reason": "Xoá watchlist", "parallel_group": 1}]
                else:
                    steps = [{"step": 1, "tool": "social", "action": "watchlist",
                              "params": {}, "reason": "Xem watchlist", "parallel_group": 1}]
            elif any(k in query_lower for k in ["xem", "list", "của tôi", "my"]):
                steps = [{"step": 1, "tool": "social", "action": "my_portfolios",
                          "params": {}, "reason": "Danh mục của tôi", "parallel_group": 1}]
            else:
                steps = [{"step": 1, "tool": "social", "action": "top_portfolios",
                          "params": {}, "reason": "Top danh mục", "parallel_group": 1}]

        elif any(k in query_lower for k in ["cảnh báo", "alert", "thông báo"]):
            if "xem" in query_lower or "list" in query_lower or "danh sách" in query_lower:
                steps = [{"step": 1, "tool": "alerts", "action": "list",
                          "params": {}, "reason": "Liệt kê cảnh báo", "parallel_group": 1}]
            elif "kiểm tra" in query_lower or "check" in query_lower:
                steps = [{"step": 1, "tool": "alerts", "action": "check",
                          "params": {}, "reason": "Kiểm tra cảnh báo", "parallel_group": 1}]
            elif "xóa" in query_lower or "delete" in query_lower:
                steps = [{"step": 1, "tool": "alerts", "action": "list",
                          "params": {}, "reason": "Liệt kê trước khi xóa", "parallel_group": 1}]
            elif "lịch sử" in query_lower or "history" in query_lower:
                steps = [{"step": 1, "tool": "alerts", "action": "history",
                          "params": {}, "reason": "Lịch sử cảnh báo", "parallel_group": 1}]
            else:
                steps = [{"step": 1, "tool": "alerts", "action": "list",
                          "params": {}, "reason": "Liệt kê cảnh báo", "parallel_group": 1}]

        # Default fallback
        if not steps:
            if symbol:
                steps = [
                    {"step": 1, "tool": "financial_ratios", "action": "all",
                     "params": {"symbol": symbol}, "reason": "Chỉ số tài chính", "parallel_group": 1},
                    {"step": 2, "tool": "technical_indicators", "action": "summary",
                     "params": {"symbol": symbol}, "reason": "Chỉ báo kỹ thuật", "parallel_group": 1},
                ]
            else:
                steps = [{"step": 1, "tool": "market_overview", "action": "summary",
                          "params": {}, "reason": "Tổng quan thị trường", "parallel_group": 1}]

        return {
            "intent": "Fallback plan",
            "symbols": symbols,
            "steps": steps,
        }


# =====================================================================
# Executor
# =====================================================================

class Executor:
    """Thực thi tools theo plan, hỗ trợ song song."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute_plan(
        self, plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute all steps in the plan.
        Steps with same parallel_group run concurrently.

        Returns:
            List of results for each step
        """
        steps = plan.get("steps", [])
        if not steps:
            return [{"error": "Không có bước nào trong kế hoạch"}]

        # Group steps by parallel_group
        groups: Dict[int, List] = {}
        for step in steps:
            pg = step.get("parallel_group", 1)
            groups.setdefault(pg, []).append(step)

        all_results = []

        # Execute groups sequentially, steps within a group concurrently
        for group_id in sorted(groups.keys()):
            group_steps = groups[group_id]
            tasks = [self._execute_step(step) for step in group_steps]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(group_steps, group_results):
                if isinstance(result, Exception):
                    all_results.append({
                        "step": step.get("step"),
                        "tool": step.get("tool"),
                        "action": step.get("action"),
                        "success": False,
                        "error": str(result),
                    })
                else:
                    all_results.append({
                        "step": step.get("step"),
                        "tool": step.get("tool"),
                        "action": step.get("action"),
                        "success": True,
                        "data": result,
                    })

        return all_results

    async def _execute_step(self, step: Dict) -> Dict[str, Any]:
        """Execute a single step."""
        tool_name = step.get("tool", "")
        action = step.get("action", "")
        params = step.get("params", {})

        tool = self.registry.get_tool(tool_name)
        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' không tồn tại",
            }

        logger.info(f"🔧 Executing: {tool_name}.{action}({params})")

        try:
            result = await tool.run(action=action, **params)
            return result
        except TypeError:
            # Some tools use positional args
            try:
                result = await tool.run(**params, action=action)
                return result
            except Exception as e:
                return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# =====================================================================
# Synthesizer
# =====================================================================

class Synthesizer:
    """Tổng hợp kết quả từ tools → Câu trả lời tiếng Việt."""

    def __init__(self, llm: LLMWrapper):
        self.llm = llm

    async def synthesize(
        self, query: str, results: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesize tool results into a human-readable response.

        Args:
            query: Original user query
            results: List of tool execution results

        Returns:
            Formatted Vietnamese response
        """
        # Format results for LLM
        results_text = self._format_results(results)

        prompt = SYNTHESIZER_PROMPT.format(
            query=query,
            results=results_text,
        )

        response = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        return response

    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format tool results into readable text for LLM."""
        sections = []
        for r in results:
            tool = r.get("tool", "unknown")
            action = r.get("action", "")
            header = f"### {tool} ({action})"

            if r.get("success"):
                data = r.get("data", {})
                # Truncate large data
                data_str = json.dumps(data, ensure_ascii=False, default=str)
                if len(data_str) > 3000:
                    data_str = data_str[:3000] + "... [truncated]"
                sections.append(f"{header}\n{data_str}")
            else:
                error = r.get("error", "Unknown error")
                sections.append(f"{header}\n❌ Error: {error}")

        return "\n\n".join(sections)


# =====================================================================
# Orchestrator - Main Agent
# =====================================================================

class AgentOrchestrator:
    """
    Main Agent Orchestrator.
    Flow: User Query → Plan → Execute → Synthesize → Response
    """

    def __init__(
        self,
        llm: Optional[LLMWrapper] = None,
        registry: Optional[ToolRegistry] = None,
        provider: str = "google",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the agent.

        Args:
            llm: Pre-configured LLMWrapper (optional)
            registry: Pre-configured ToolRegistry (optional)
            provider: LLM provider if llm not given
            model: LLM model name if llm not given
            api_key: API key if llm not given
        """
        # Initialize LLM
        if llm is not None:
            self.llm = llm
        else:
            self.llm = LLMWrapper(
                provider=provider,
                model=model,
                api_key=api_key,
            )

        # Initialize Registry & register tools
        if registry is not None:
            self.registry = registry
        else:
            self.registry = register_all_tools()

        # Initialize components
        self.planner = Planner(self.llm, self.registry)
        self.executor = Executor(self.registry)
        self.synthesizer = Synthesizer(self.llm)
        self.memory = ConversationMemory()

        logger.info(
            f"🤖 Agent initialized: provider={self.llm.provider}, "
            f"model={self.llm.model}, "
            f"tools={self.registry.get_tool_names()}"
        )

    async def chat(self, query: str) -> str:
        """
        Process a user query end-to-end.

        Args:
            query: Natural language query in Vietnamese

        Returns:
            Vietnamese analysis response
        """
        start_time = time.time()

        # Quick responses for greetings / non-analysis queries
        if self._is_greeting(query):
            response = (
                "Xin chào! Tôi là **Dexter** — trợ lý AI phân tích chứng khoán Việt Nam. 🇻🇳\n\n"
                "Tôi có thể giúp bạn:\n"
                "- 📊 Phân tích cơ bản & kỹ thuật cổ phiếu (VD: *Phân tích VNM*)\n"
                "- 💰 Theo dõi dòng tiền khối ngoại (VD: *Khối ngoại mua gì?*)\n"
                "- 📰 Tin tức & tâm lý thị trường (VD: *Tin tức FPT*)\n"
                "- 🔍 Sàng lọc cổ phiếu (VD: *Lọc CP giá trị*)\n"
                "- 📈 Tổng quan thị trường (VD: *Thị trường hôm nay?*)\n"
                "- 🎯 Định giá DCF (VD: *Định giá VCB*)\n\n"
                "Hãy hỏi tôi bất cứ điều gì!"
            )
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", response)
            return response

        try:
            # Step 1: Plan
            logger.info(f"📋 Planning for: {query}")
            context = self.memory.get_context(last_n=3)
            plan = await self.planner.create_plan(query, context)
            logger.info(f"📋 Plan: {json.dumps(plan, ensure_ascii=False, default=str)[:300]}")

            # Step 2: Execute
            logger.info(f"⚡ Executing {len(plan.get('steps', []))} steps...")
            results = await self.executor.execute_plan(plan)

            # Step 3: Synthesize
            logger.info("📝 Synthesizing response...")
            response = await self.synthesizer.synthesize(query, results)

            # Build tool usage summary
            elapsed = time.time() - start_time
            tool_summary = self._build_tool_summary(plan, results, elapsed)
            response = tool_summary + "\n\n" + response

            # Record in memory
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", response)

            logger.info(f"✅ Completed in {elapsed:.1f}s")

            return response

        except Exception as e:
            logger.error(f"❌ Agent error: {e}", exc_info=True)
            error_msg = (
                f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi: {str(e)}\n\n"
                "Vui lòng thử lại hoặc đặt câu hỏi khác."
            )
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", error_msg)
            return error_msg

    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting / help request."""
        greetings = [
            "xin chào", "hello", "hi", "chào", "hey",
            "help", "giúp", "hướng dẫn", "bắt đầu",
            "bạn là ai", "who are you", "dexter",
        ]
        q = query.lower().strip()
        return any(q.startswith(g) or q == g for g in greetings)

    def _build_tool_summary(
        self, plan: Dict[str, Any], results: List[Dict[str, Any]], elapsed: float
    ) -> str:
        """Build a summary of tools used for the response."""
        lines = ["---", "📦 **Tools đã sử dụng:**"]

        for r in results:
            tool = r.get("tool", "?")
            action = r.get("action", "?")
            success = r.get("success", False)
            icon = "✅" if success else "❌"
            lines.append(f"  {icon} `{tool}` → `{action}`")

        intent = plan.get("intent", "")
        if intent:
            lines.append(f"\n🎯 **Ý định:** {intent}")

        lines.append(f"⏱️ **Thời gian:** {elapsed:.1f}s")
        lines.append("---")

        return "\n".join(lines)

    async def direct_tool_call(
        self, tool_name: str, action: str, **params
    ) -> Dict[str, Any]:
        """
        Call a tool directly without going through the full pipeline.
        Useful for programmatic access.
        """
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        try:
            return await tool.run(action=action, **params)
        except Exception as e:
            return {"success": False, "error": str(e)}
