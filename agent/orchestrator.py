
import json
import time
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from dexter_vietnam.model.llm import LLMWrapper
from dexter_vietnam.tools.registry import ToolRegistry, register_all_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là **Dexter** — trợ lý AI phân tích chứng khoán Việt Nam 🇻🇳, được xây dựng để hỗ trợ nhà đầu tư phân tích và ra quyết định dựa trên dữ liệu thực tế.

## 📋 Quy tắc BẮT BUỘC khi gọi tool
1. **Luôn điền tham số `reason`** — giải thích ngắn gọn TẠI SAO cần gọi tool này.
2. **Mỗi tool call chỉ nhận 1 symbol** (string). Khi so sánh 2+ cổ phiếu → gọi tool **riêng** cho từng symbol.
3. **Đại từ thay thế** ("nó", "cổ phiếu đó", "mã đó") → tra lịch sử hội thoại để xác định đúng symbol.
4. **Chỉ gọi tool khi cần dữ liệu thực tế.** Câu hỏi chung (chào hỏi, hỏi bạn là ai) → trả lời trực tiếp, không gọi tool.
5. **Chỉ gọi tool trong schema.** Không tự tạo tool. Có thể phân tích/kết hợp kết quả từ tool trước khi gọi tool tiếp.
6. **Khi tool trả về lỗi hoặc `success: false`** → thông báo rõ cho user, KHÔNG tự bịa hoặc ước tính số liệu.

## 📊 Quy tắc trả lời
- Trả lời **tiếng Việt**, chuyên nghiệp, dễ hiểu
- **Luôn dùng số liệu cụ thể** từ kết quả tool — không nói chung chung
- **Nêu rõ khoảng thời gian** dữ liệu thực tế (dùng `actual_start` / `actual_end` nếu có)
- **Format output phù hợp ngữ cảnh:**
  - So sánh cổ phiếu → dùng **bảng (table)**
  - Danh sách tín hiệu / rủi ro → dùng **bullet points**
  - Phân tích đơn lẻ → dùng **headings** phân chia rõ ràng
- **Nếu thiếu dữ liệu** → nói rõ phần nào thiếu, phân tích phần có data
- **Kết luận ngắn gọn** cuối mỗi phân tích

## 📅 Ngày hôm nay: {current_date}
"""


class ConversationMemory:

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.history: List[Dict] = []
        self.active_symbols: List[str] = []

    def add_turn(self, role: str, content: str, symbols: Optional[List[str]] = None):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "symbols": symbols or [],
        })
        if symbols:
            self.active_symbols = symbols
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_messages_for_llm(self, last_n: int = 6) -> List[Dict[str, str]]:
        recent = self.history[-last_n * 2:]
        msgs: List[Dict[str, str]] = []
        for turn in recent:
            role = turn["role"]
            if role in ("user", "assistant"):
                msgs.append({"role": role, "content": turn["content"][:800]})
        if self.active_symbols:
            msgs.append({
                "role": "user",
                "content": f"[Context: cổ phiếu đang thảo luận: {', '.join(self.active_symbols)}]",
            })
        return msgs

    def clear(self):
        self.history = []
        self.active_symbols = []


class AgentOrchestrator:

    MAX_TOOL_ROUNDS = 20

    def __init__(
        self,
        llm: Optional[LLMWrapper] = None,
        registry: Optional[ToolRegistry] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        self.llm = llm or LLMWrapper(model=model, api_key=api_key)
        self.registry = registry or register_all_tools()
        self.memory = ConversationMemory()
        self._tool_schemas = self.registry.get_function_schemas()

        logger.info(
            f"🤖 Orchestrator ready: {self.llm.model}, "
            f"tools={len(self.registry.get_all_tools())}, "
            f"functions={len(self._tool_schemas)}"
        )

    def chat(self, query: str) -> str:

        start_time = time.time()

        if self._is_greeting(query):
            response = self._greeting_response()
            self.memory.add_turn("user", query)
            self.memory.add_turn("assistant", response)
            return response

        try:
            system_prompt = SYSTEM_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )

            messages: List[Dict[str, Any]] = self.memory.get_messages_for_llm(last_n=4)
            messages.append({"role": "user", "content": query})

            tool_log: List[Dict[str, Any]] = []
            reasons: List[str] = []

            for round_idx in range(self.MAX_TOOL_ROUNDS):
                logger.info(f"🔄 Function-calling round {round_idx + 1}")

                result = self.llm.generate_with_tools(
                    messages=messages,
                    tools=self._tool_schemas,
                    system_prompt=system_prompt,
                )

                tool_calls = result.get("tool_calls", [])

                if not tool_calls:
                    final_text = result.get("content") or ""
                    break

                api_tool_calls = []
                for tc in tool_calls:
                    api_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function_name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    })
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": result.get("content") or "",
                    "tool_calls": api_tool_calls,
                }
                messages.append(assistant_msg)

                for tc in tool_calls:
                    fn_name = tc["function_name"]
                    args = tc["arguments"]
                    call_id = tc["id"]

                    reason = args.pop("reason", "Không nêu lý do")
                    reasons.append(f"**{fn_name}**: {reason}")
                    logger.info(f"📌 Tool call: {fn_name} | Reason: {reason}")

                    tool, action = self.registry.resolve_function_name(fn_name)

                    if tool is None:
                        tool_result = {"success": False, "error": f"Tool '{fn_name}' không tồn tại"}
                        tool_log.append({"tool": fn_name, "success": False})
                    else:
                        if "symbol" in args and isinstance(args["symbol"], list):
                            args["symbol"] = args["symbol"][0] if args["symbol"] else ""

                        logger.info(f"🔧 Executing: {fn_name}({args})")
                        try:
                            tool_result = tool.run(action=action, **args)
                            tool_log.append({
                                "tool": fn_name,
                                "success": tool_result.get("success", False),
                            })
                        except Exception as e:
                            logger.error(f"❌ Error executing {fn_name}: {e}")
                            tool_result = {"success": False, "error": str(e)}
                            tool_log.append({"tool": fn_name, "success": False})

                    result_str = json.dumps(self._sanitize_keys(tool_result), ensure_ascii=False, default=str)
                    if len(result_str) > 6000:
                        result_str = result_str[:6000] + "\n... [truncated]"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": fn_name,
                        "content": result_str,
                    })

            else:
                final_text = (
                    "Xin lỗi, tôi đã thực hiện quá nhiều bước mà chưa đưa ra được "
                    "câu trả lời hoàn chỉnh. Vui lòng thử lại với câu hỏi cụ thể hơn."
                )

            elapsed = time.time() - start_time
            summary = self._build_summary(tool_log, reasons, elapsed)
            final_response = summary + "\n\n" + final_text if tool_log else final_text

            symbols = self._extract_symbols(query)
            self.memory.add_turn("user", query, symbols=symbols)
            self.memory.add_turn("assistant", final_text, symbols=symbols)

            logger.info(f"✅ Completed in {elapsed:.1f}s, {len(tool_log)} tool calls")
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
        greetings = ["xin chào", "hello", "hi", "chào", "hey", "help"]
        q = query.lower().strip()
        return any(q.startswith(g) or q == g for g in greetings)

    def _greeting_response(self) -> str:
        return (
            "Xin chào! Tôi là **Dexter** — trợ lý AI phân tích chứng khoán Việt Nam 🇻🇳\n\n"
            "Tôi có thể giúp bạn:\n"
            "- 📊 Phân tích cổ phiếu (VD: *Phân tích FPT*)\n"
            "- ⚖️ So sánh cổ phiếu (VD: *So sánh FPT và VNM*)\n"
            "- 💰 Khối ngoại mua/bán gì (VD: *Khối ngoại mua gì?*)\n"
            "- 📰 Tin tức thị trường (VD: *Tin tức VNM*)\n"
            "- 🔍 Lọc cổ phiếu (VD: *Lọc cổ phiếu giá trị*)\n"
            "- 📈 Tổng quan thị trường (VD: *Thị trường hôm nay?*)\n\n"
            "Hãy hỏi tôi bất cứ điều gì!"
        )

    def _build_summary(self, tool_log, reasons, elapsed):
        if not tool_log:
            return ""
        lines = ["---", "📦 **Tools đã sử dụng:**"]
        for entry in tool_log:
            tool = entry.get("tool", "?")
            success = entry.get("success", False)
            icon = "✅" if success else "❌"
            lines.append(f"  {icon} `{tool}`")
        if reasons:
            lines.append("")
            lines.append("💡 **Lý do gọi tool:**")
            for r in reasons:
                lines.append(f"  - {r}")
        lines.append(f"\n⏱️ **Thời gian:** {elapsed:.1f}s")
        lines.append("---")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                str(k) if isinstance(k, tuple) else k: AgentOrchestrator._sanitize_keys(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [AgentOrchestrator._sanitize_keys(i) for i in obj]
        if isinstance(obj, tuple):
            return [AgentOrchestrator._sanitize_keys(i) for i in obj]
        return obj

    @staticmethod
    def _extract_symbols(query: str) -> List[str]:
        symbols = re.findall(r'\b([A-Z]{3})\b', query)
        stop_words = {"VND", "USD", "GDP", "ETF", "CEO", "CFO", "CPI", "SMA", "EMA", "RSI"}
        return [s for s in symbols if s not in stop_words]


