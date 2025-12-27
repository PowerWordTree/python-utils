from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UIMessageProtocol(Protocol):
    def get_message(self) -> str: ...


@runtime_checkable
class UIProtocol(Protocol):
    def render(self, message: str | UIMessageProtocol) -> None: ...
    def error(self, message: str | UIMessageProtocol) -> None: ...
