from __future__ import annotations

import sys
from typing import Any, Callable

from pwt.winenv_cli.ui.protocol import UIMessageProtocol, UIProtocol


class BaseUIMessage(UIMessageProtocol):
    def __init__(self, text: str, *args: Any, **kwargs: Any):
        self.text = text
        self.args = args
        self.kwargs = kwargs

    def get_message(self) -> str:
        return self.text.format(*self.args, **self.kwargs)


class BaseCliUI(UIProtocol):
    def render(self, message: str | UIMessageProtocol) -> None:
        if isinstance(message, UIMessageProtocol):
            print(message.get_message())
        else:
            print(message)

    def error(self, message: str | UIMessageProtocol) -> None:
        if isinstance(message, UIMessageProtocol):
            print(message.get_message(), file=sys.stderr)
        else:
            print(message, file=sys.stderr)


class UIRegistry:
    registry: dict[str, Callable[[], UIProtocol]] = {}
    default: str = ""

    @classmethod
    def register(cls, name: str = "", *, default: bool = False):
        def wrapper(view_cls: Callable[[], UIProtocol]):
            key = name.strip() or view_cls.__name__
            cls.registry[key] = view_cls
            if default:
                cls.default = key
            return view_cls

        return wrapper

    @classmethod
    def get(cls, name: str) -> Callable[[], UIProtocol] | None:
        return cls.registry.get(name)

    @classmethod
    def get_default(cls) -> Callable[[], UIProtocol]:
        return cls.get(cls.default) or BaseCliUI

    @classmethod
    def set_default(cls, name: str):
        cls.default = name

    @classmethod
    def available(cls) -> list[str]:
        return list(cls.registry.keys())
