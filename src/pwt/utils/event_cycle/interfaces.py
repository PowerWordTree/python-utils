"""
定义事件循环中使用的协议接口, 包括资源表示/事件处理器和错误回调等.

这些协议用于实现组件解耦, 支持类型检查与行为契约:
    - SupportsFileno: 抽象资源对象(如 socket), 用于 selector 注册.
    - EventDoneFunc: 通知事件处理完成的回调函数.
    - EventHandler: 读写事件的处理器协议, 支持同步或异步返回.
    - ErrorHandler: 用于处理调度期间发生的异常.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pwt.utils.event_cycle.core import ContextManager
    from pwt.utils.event_cycle.errors import EventCycleError


@runtime_checkable
class SupportsFileno(Protocol):
    """定义支持 `fileno()` 方法的对象, 用于 selector 注册."""

    def fileno(self) -> int: ...


@runtime_checkable
class EventDoneFunc(Protocol):
    """事件处理完成回调, 用于通知是否继续推进事件循环."""

    def __call__(self, resume: bool = True) -> None: ...


@runtime_checkable
class EventHandler(Protocol):
    """事件处理器接口, 用于处理读/写事件, 可返回同步结果或异步 Future."""

    def __call__(
        self, target: FileDescriptorLike, extra: Any, done: EventDoneFunc
    ) -> bool | Future | None: ...


@runtime_checkable
class ErrorHandler(Protocol):
    """错误处理器接口, 用于处理调度器内部异常并决定是否恢复."""

    def __call__(
        self,
        exc: EventCycleError,
        manager: ContextManager,
        target: FileDescriptorLike | None,
    ) -> bool: ...


FileDescriptor = int
FileDescriptorLike = FileDescriptor | SupportsFileno
EventMask = int  # selectors.EVENT_READ | selectors.EVENT_WRITE
