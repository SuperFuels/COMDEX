from __future__ import annotations

from typing import Any, Dict, List, Optional


class OperatorRegistry:
    def __init__(self) -> None:
        self._operators: Dict[str, Any] = {}

    def register(self, operator: Any) -> Any:
        operator_id = getattr(operator, "id", None) or getattr(operator, "operator_id", None)
        if not operator_id:
            raise ValueError("Operator must expose id or operator_id")
        self._operators[str(operator_id)] = operator
        return operator

    def register_operator(self, operator: Any) -> Any:
        return self.register(operator)

    def get(self, operator_id: str) -> Optional[Any]:
        return self._operators.get(operator_id)

    def get_operator(self, operator_id: str) -> Optional[Any]:
        return self.get(operator_id)

    def list(self) -> List[Any]:
        return list(self._operators.values())

    def list_operators(self) -> List[Any]:
        return self.list()

    def has(self, operator_id: str) -> bool:
        return operator_id in self._operators

    def clear(self) -> None:
        self._operators.clear()