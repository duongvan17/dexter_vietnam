"""
Base Tool class
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseTool(ABC):
    """Base class for all tools"""

    @abstractmethod
    def get_name(self) -> str:
        """Return tool name"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return tool description for LLM"""
        pass

    @abstractmethod
    def get_actions(self) -> Dict[str, str]:
        """Return supported actions: {action_name: short_description}"""
        pass

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool (synchronous)"""
        pass

    # ------------------------------------------------------------------
    # Native function-calling support
    # ------------------------------------------------------------------

    def get_parameters_schema(self) -> Dict[str, Dict[str, Any]]:
        """Return per-action JSON-Schema for parameters."""
        actions = self.get_actions()
        no_symbol = getattr(self, "_no_symbol_actions", set())
        schemas: Dict[str, Dict[str, Any]] = {}

        for action_name in actions:
            if action_name in no_symbol:
                schemas[action_name] = {
                    "properties": {},
                    "required": [],
                }
            else:
                schemas[action_name] = {
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Mã cổ phiếu (VD: FPT, VNM, HPG)",
                        }
                    },
                    "required": ["symbol"],
                }
        return schemas

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Generate OpenAI-compatible function schemas for each action."""
        tool_name = self.get_name()
        actions = self.get_actions()
        param_schemas = self.get_parameters_schema()
        functions: List[Dict[str, Any]] = []

        for action_name, action_desc in actions.items():
            ps = param_schemas.get(action_name, {"properties": {}, "required": []})
            properties = dict(ps.get("properties", {}))
            required = list(ps.get("required", []))

            # Inject mandatory "reason" parameter
            properties["reason"] = {
                "type": "string",
                "description": (
                    "Lý do bạn gọi tool này — giải thích ngắn gọn tại sao "
                    "cần dữ liệu/phân tích này để trả lời câu hỏi của user."
                ),
            }
            required.append("reason")

            functions.append({
                "type": "function",
                "function": {
                    "name": f"{tool_name}__{action_name}",
                    "description": f"[{tool_name}] {action_desc}",
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })

        return functions
