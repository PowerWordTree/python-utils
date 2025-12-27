from __future__ import annotations

import logging
from typing import Any

from pwt.utils.log import helpers

from pwt.utils.ui.base import BaseUIMessage, UIRegistry
from pwt.utils.ui.protocol import UIMessageProtocol, UIProtocol


class LoggingUIMessage(BaseUIMessage):
    def __init__(self, level: str | int, text: str, *args: Any, **kwargs: Any):
        super().__init__(text, *args, **kwargs)
        self.level = level if isinstance(level, int) else helpers.get_level(level)

    @staticmethod
    def build(
        msg: str | UIMessageProtocol, level: str | int = logging.INFO
    ) -> LoggingUIMessage:
        if isinstance(msg, LoggingUIMessage):
            return msg
        if isinstance(msg, UIMessageProtocol):
            msg = msg.get_message()
        return LoggingUIMessage(level or logging.INFO, msg)


class LoggingCliUI(UIProtocol):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log(self, msg: str | UIMessageProtocol) -> None:
        if not isinstance(msg, LoggingUIMessage):
            msg = LoggingUIMessage.build(msg)
        kwargs = dict(msg.kwargs)  # 浅拷贝
        extra = kwargs.pop("extra", {})
        kwargs = {**extra, "extra": kwargs}
        self.logger.log(msg.level, msg.get_message(), *msg.args, **kwargs)

    def render(self, msg: str | UIMessageProtocol) -> None:
        self.log(msg)

    def error(self, msg: str | UIMessageProtocol) -> None:
        self.log(msg)


def register_logging_ui(logger: logging.Logger, default: bool = False) -> None:
    UIRegistry.register("logging", default=default)(lambda: LoggingCliUI(logger))
