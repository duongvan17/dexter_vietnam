
import asyncio
import json
import time
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from dexter_vietnam.model.llm import LLMWrapper
from dexter_vietnam.tools.registry import ToolRegistry, register_all_tools

logger = logging.getLogger(__name__)


PLANNER_PROMPT = """Bạn là AI planner cho hệ thống phân tích chứng khoán Việt Nam.

NHIỆM VỤ: Phân tích câu hỏi và tạo plan để gọi các tools cần thiết.

## Tools có sẵn:
{tools_description}

## Format output (JSON):
{{
    "intent": "mô tả ngắn gọn ý định",
    "symbols": ["VNM", "FPT"],
    "steps": [
        {{
            "step": 1,
            "tool": "tool_name",
            "action": "action_name", 
            "params": {{"symbol": "VNM"}},
            "reason": "tại sao cần tool này"
        }}
    ]
}}

## Lưu ý quan trọng:
1. **vnstock_connector** - Tool lấy dữ liệu thô từ vnstock:
   - Actions: stock_overview, stock_price, financial_ratio, financial_report, foreign_trading, all_symbols, market_index
   - Luôn dùng khi cần thông tin công ty, giá, BCTC

2. **financial_ratios** - Tool phân tích chỉ số tài chính:
   - Actions: all, valuation, profitability, liquidity, leverage
   - Dùng để tính toán và đánh giá chỉ số

3. **technical_indicators** - Chỉ báo kỹ thuật:
   - Actions: all, summary, rsi, macd, bollinger, moving_averages

4. Các tools khác: market_overview, news_aggregator, stock_screener, dcf_valuation, etc.

## Ví dụ:
- "Phân tích FPT" → vnstock_connector(stock_overview) + financial_ratios(all) + technical_indicators(summary)
- "Thông tin VNM" → vnstock_connector(stock_overview) + vnstock_connector(stock_price)
- "Thị trường hôm nay" → market_overview(summary)

Câu hỏi: {query}
"""

SYNTHESIZER_PROMPT = """Bạn là AI phân tích chứng khoán Việt Nam.

Dựa trên dữ liệu từ tools, hãy tổng hợp câu trả lời tiếng Việt chuyên nghiệp.

## Câu hỏi:
{query}

## Dữ liệu từ tools:
{results}

## Yêu cầu:
- Trả lời bằng tiếng Việt, chuyên nghiệp, dễ hiểu
- **Luôn nêu rõ khoảng thời gian DỮ LIỆU THỰC TẾ** (dùng `actual_start` và `actual_end` từ data, KHÔNG dùng `requested_start/end`)
- Nếu data chỉ có đến ngày cũ hơn ngày hiện tại, nói rõ: "Dữ liệu mới nhất đến ngày X"
- Dùng số liệu cụ thể từ dữ liệu
- Đưa ra phân tích và nhận định
- Format markdown đẹp: headings, bullets, tables
- Nếu thiếu dữ liệu, nói rõ và phân tích phần có data
- Kết luận ngắn gọn

## Lưu ý về thời gian:
- Ngày hôm nay: {current_date}
- Nếu `actual_end` < ngày hôm nay → Nói rõ "Dữ liệu mới nhất: [actual_end]"
- Luôn dùng `actual_start` và `actual_end` thay vì `requested_start` và `requested_end`
"""

class ConversationMemory:
    """Lưu lịch sử hội thoại."""
    
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []
    
    def add_turn(self, role: str, content: str) -> None:
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]
    
    def get_context(self, last_n: int = 3) -> str:
        """Lấy N turn gần nhất."""
        recent = self.history[-last_n * 2:]
        if not recent:
            return ""
        lines = []
        for turn in recent:
            role = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{role}: {turn['content'][:200]}")
        return "\n".join(lines)
    
    def clear(self) -> None:
        self.history = []

class Planner:
    
    def __init__(self, llm: LLMWrapper, registry: ToolRegistry):
        self.llm = llm
        self.registry = registry
    
    async def create_plan(self, query: str, context: str = "") -> Dict[str, Any]:
  
        tools_desc = self.registry.get_tools_description()
        
        prompt = PLANNER_PROMPT.format(
            tools_description=tools_desc,
            query=query
        )
        
        if context:
            prompt += f"\n\n## Context hội thoại:\n{context}"
        
        try:
            # Gọi LLM để tạo plan
            plan = await self.llm.generate_json(prompt)
            
            # Validate
            if "steps" not in plan or not plan["steps"]:
                logger.warning("LLM plan invalid, using simple fallback")
                return self._simple_fallback(query)
            
            logger.info(f"✅ LLM Plan created: {len(plan['steps'])} steps")
            return plan
            
        except Exception as e:
            logger.warning(f"LLM planner failed: {e}, using fallback")
            return self._simple_fallback(query)
    
    def _simple_fallback(self, query: str) -> Dict[str, Any]:
        """
        Fallback đơn giản: phân tích symbol và gọi tools cơ bản.
        """
        query_lower = query.lower()
        
        # Extract symbols
        symbols = re.findall(r'\b([A-Z]{3})\b', query)
        stop_words = {"VND", "USD", "GDP", "ETF", "CEO", "CFO"}
        symbols = [s for s in symbols if s not in stop_words]
        
        symbol = symbols[0] if symbols else ""
        
        steps = []
        
        # Nếu có symbol → lấy thông tin cơ bản
        if symbol:
            steps = [
                {"step": 1, "tool": "vnstock_connector", "action": "stock_overview",
                 "params": {"symbol": symbol}, "reason": "Thông tin công ty"},
                {"step": 2, "tool": "vnstock_connector", "action": "stock_price",
                 "params": {"symbol": symbol}, "reason": "Lịch sử giá"},
            ]
            
            # Thêm tools khác dựa trên keywords
            if any(k in query_lower for k in ["phân tích", "đánh giá", "chỉ số"]):
                steps.append(
                    {"step": 3, "tool": "financial_ratios", "action": "all",
                     "params": {"symbol": symbol}, "reason": "Chỉ số tài chính"}
                )
            
            if any(k in query_lower for k in ["kỹ thuật", "rsi", "macd", "technical"]):
                steps.append(
                    {"step": 4, "tool": "technical_indicators", "action": "summary",
                     "params": {"symbol": symbol}, "reason": "Chỉ báo kỹ thuật"}
                )
        
        # Không có symbol → thị trường tổng quan
        else:
            if any(k in query_lower for k in ["thị trường", "market", "vnindex"]):
                steps = [
                    {"step": 1, "tool": "market_overview", "action": "summary",
                     "params": {}, "reason": "Tổng quan thị trường"}
                ]
            elif any(k in query_lower for k in ["khối ngoại", "foreign"]):
                steps = [
                    {"step": 1, "tool": "money_flow", "action": "top_foreign_buy",
                     "params": {}, "reason": "Khối ngoại mua"}
                ]
            elif any(k in query_lower for k in ["tin", "news", "tin tức"]):
                steps = [
                    {"step": 1, "tool": "news_aggregator", "action": "market",
                     "params": {}, "reason": "Tin tức thị trường"}
                ]
            else:
                # Default: market overview
                steps = [
                    {"step": 1, "tool": "market_overview", "action": "summary",
                     "params": {}, "reason": "Tổng quan thị trường"}
                ]
        
        return {
            "intent": "Simple fallback plan",
            "symbols": symbols,
            "steps": steps
        }


# =====================================================================
# Executor
# =====================================================================

class Executor:
    """Thực thi tools theo plan."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    async def execute_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute tất cả steps trong plan."""
        steps = plan.get("steps", [])
        if not steps:
            return [{"error": "Không có steps trong plan"}]
        
        results = []
        
        # Execute từng step tuần tự
        for step in steps:
            result = await self._execute_step(step)
            results.append({
                "step": step.get("step"),
                "tool": step.get("tool"),
                "action": step.get("action"),
                "success": result.get("success", False),
                "data": result if result.get("success") else {"error": result.get("error")}
            })
        
        return results
    
    async def _execute_step(self, step: Dict) -> Dict[str, Any]:
        """Execute một step."""
        tool_name = step.get("tool", "")
        action = step.get("action", "")
        params = step.get("params", {})
        
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' không tồn tại"}
        
        logger.info(f"🔧 Executing: {tool_name}.{action}({params})")
        
        try:
            result = await tool.run(action=action, **params)
            return result
        except Exception as e:
            logger.error(f"❌ Error executing {tool_name}.{action}: {e}")
            return {"success": False, "error": str(e)}


# =====================================================================
# Synthesizer
# =====================================================================

class Synthesizer:
    """Tổng hợp kết quả từ tools thành câu trả lời."""
    
    def __init__(self, llm: LLMWrapper):
        self.llm = llm
    
    async def synthesize(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Gọi LLM để tổng hợp kết quả."""
        results_text = self._format_results(results)
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        prompt = SYNTHESIZER_PROMPT.format(
            query=query,
            results=results_text,
            current_date=current_date
        )
        
        response = await self.llm.generate(prompt)
        return response
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format kết quả thành text cho LLM."""
        sections = []
        
        for r in results:
            tool = r.get("tool", "unknown")
            action = r.get("action", "")
            success = r.get("success", False)
            
            header = f"## Tool: {tool} → {action}"
            
            if success:
                data = r.get("data", {})
                # Truncate nếu quá dài
                data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
                if len(data_str) > 4000:
                    data_str = data_str[:4000] + "\n... [truncated]"
                sections.append(f"{header}\n✅ Success\n```json\n{data_str}\n```")
            else:
                error_data = r.get("data", {})
                error = error_data.get("error", "Unknown error")
                sections.append(f"{header}\n❌ Error: {error}")
        
        return "\n\n".join(sections)


# =====================================================================
# Orchestrator
# =====================================================================

class AgentOrchestrator:
    """Main orchestrator - đơn giản hóa, để LLM tự quyết định."""
    
    def __init__(
        self,
        llm: Optional[LLMWrapper] = None,
        registry: Optional[ToolRegistry] = None,
        provider: str = "google",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # Initialize LLM
        if llm is not None:
            self.llm = llm
        else:
            self.llm = LLMWrapper(provider=provider, model=model, api_key=api_key)
        
        # Initialize Registry
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
            f"🤖 Orchestrator initialized: {self.llm.provider}/{self.llm.model}, "
            f"tools={len(self.registry.get_all_tools())}"
        )
    
    async def chat(self, query: str) -> str:
        """Xử lý câu hỏi của user."""
        start_time = time.time()
        
        # Greeting
        if self._is_greeting(query):
            response = self._greeting_response()
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", response)
            return response
        
        try:
            # Step 1: Plan
            logger.info(f"📋 Planning for: {query}")
            context = self.memory.get_context(last_n=2)
            plan = await self.planner.create_plan(query, context)
            
            # Step 2: Execute
            logger.info(f"⚡ Executing {len(plan.get('steps', []))} steps...")
            results = await self.executor.execute_plan(plan)
            
            # Step 3: Synthesize
            logger.info("📝 Synthesizing response...")
            response = await self.synthesizer.synthesize(query, results)
            
            # Add summary
            elapsed = time.time() - start_time
            summary = self._build_summary(plan, results, elapsed)
            final_response = summary + "\n\n" + response
            
            # Save to memory
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", final_response)
            
            logger.info(f"✅ Completed in {elapsed:.1f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            error_msg = (
                f"Xin lỗi, có lỗi xảy ra: {str(e)}\n\n"
                "Vui lòng thử lại hoặc đặt câu hỏi khác."
            )
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", error_msg)
            return error_msg
    
    def _is_greeting(self, query: str) -> bool:
        """Check greeting."""
        greetings = ["xin chào", "hello", "hi", "chào", "hey", "help"]
        q = query.lower().strip()
        return any(q.startswith(g) or q == g for g in greetings)
    
    def _greeting_response(self) -> str:
        """Greeting message."""
        return (
            "Xin chào! Tôi là **Dexter** — trợ lý AI phân tích chứng khoán Việt Nam 🇻🇳\n\n"
            "Tôi có thể giúp bạn:\n"
            "- 📊 Phân tích cổ phiếu (VD: *Phân tích FPT*)\n"
            "- 💰 Khối ngoại mua/bán gì (VD: *Khối ngoại mua gì?*)\n"
            "- 📰 Tin tức thị trường (VD: *Tin tức VNM*)\n"
            "- 🔍 Lọc cổ phiếu (VD: *Lọc cổ phiếu giá trị*)\n"
            "- 📈 Tổng quan thị trường (VD: *Thị trường hôm nay?*)\n\n"
            "Hãy hỏi tôi bất cứ điều gì!"
        )
    
    def _build_summary(
        self, plan: Dict[str, Any], results: List[Dict[str, Any]], elapsed: float
    ) -> str:
        """Build summary."""
        lines = ["---", "📦 **Tools:**"]
        
        for r in results:
            tool = r.get("tool", "?")
            action = r.get("action", "?")
            success = r.get("success", False)
            icon = "✅" if success else "❌"
            lines.append(f"  {icon} `{tool}.{action}`")
        
        lines.append(f"\n⏱️ **Thời gian:** {elapsed:.1f}s")
        lines.append("---")
        
        return "\n".join(lines)
    
    async def direct_tool_call(
        self, tool_name: str, action: str, **params
    ) -> Dict[str, Any]:
        """Gọi tool trực tiếp."""
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        try:
            return await tool.run(action=action, **params)
        except Exception as e:
            return {"success": False, "error": str(e)}
