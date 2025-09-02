from __future__ import annotations

import logging
from typing import Any, Literal

from pwt.utils.expression import Expression


class FieldFilter(logging.Filter):
    """
    日志字段规则过滤器
    """

    def __init__(
        self,
        *conditions: str,
        context: dict[str, Any] | None = None,
        policy: Literal["allow", "deny"] = "allow",
    ) -> None:
        """
        初始化过滤器

        参数:
            conditions: 用于匹配日志记录的表达式字符串列表
            policy: 过滤策略. allow: 允许; deny: 拒绝;
        """
        super().__init__()
        self.context = context
        self.policy = policy
        self.rules = [
            Expression(expr) for condition in conditions if (expr := condition.strip())
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用于过滤日志记录的回调函数

        参数:
            record: 要过滤的日志记录
        返回:
            如果规则匹配, 则返回 True, 否则返回 False
        """
        try:
            matched = any(
                rule.match(**(self.context or {}), record=record) for rule in self.rules
            )
        except Exception:
            matched = False

        if self.policy == "deny":
            return not matched
        return matched
