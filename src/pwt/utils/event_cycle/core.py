"""
事件循环调度器核心实现模块.

该模块定义事件驱动系统的主调度器, 提供异步事件监听/处理器调用与资源状态协调等功能. 

模块结构:
    - EventCycle: 核心类, 包含事件循环控制与资源注册机制
"""

from __future__ import annotations

import contextlib
import selectors
from concurrent.futures import Future
from functools import partial
from typing import Any, Literal

from pwt.utils.event_cycle.context import ContextManager
from pwt.utils.event_cycle.errors import (
    CycleReadHandlerError,
    CycleSelectError,
    CycleWriteHandlerError,
    EventCycleError,
)
from pwt.utils.event_cycle.interfaces import (
    ErrorHandler,
    EventHandler,
    EventMask,
    FileDescriptorLike,
)
from pwt.utils.event_cycle.notifier import Notifier, create_notifier


class EventCycle:
    """
    事件循环调度器, 用于协调资源事件与处理器调用. 

    调度逻辑基于 `selectors` 模块实现事件监听; 
    指令注入通过 `Notifier` 管理, 确保线程安全; 
    资源状态由 `ContextManager` 管理, 并支持惰性更新以提升性能; 
    异常处理支持局部 `ErrorHandler` 与全局回退机制, 未处理错误将直接抛出. 
    """

    def __init__(self, selector: selectors.BaseSelector | None = None) -> None:
        """
        初始化事件循环调度器. 

        Args:
            selector: 可选, 事件监听器实例. 
                若未提供则使用 `selectors.DefaultSelector`. 
        """
        self.error_handler: ErrorHandler | None = None
        self.closed = False
        self._selector = selector or selectors.DefaultSelector()
        self._context_manager = ContextManager()
        self._notifier: Notifier[tuple[Any, ...]] = create_notifier()
        self._selector.register(self._notifier, selectors.EVENT_READ)

    def run_cycle(self, run_once: bool = False, timeout: float | None = None) -> None:
        """
        启动事件循环调度流程. 

        该方法会阻塞执行, 持续监听已注册资源的 I/O 事件并分发给对应处理器. 
        无需强制在独立线程中运行, 但调用方需确保阻塞行为符合调度需求. 

        调度过程中, 所有异常会通过 ErrorHandler 机制进行处理: 
          - 若 ErrorHandler 返回 True, 视为异常已处理, 事件循环继续; 
          - 若返回 False, 则立即终止循环, 不抛出异常; 
          - 若 ErrorHandler 抛出异常, 则该异常会向上抛出, 循环终止. 

        Args:
            run_once: 是否仅执行一次调度周期. 
                若为 True, 则处理完当前事件后立即返回. 
            timeout: selector 的监听超时, 单位秒. 
                若为 None, 则持续阻塞直到有事件发生. 

        Raises:
            Exception: 当 ErrorHandler 抛出异常时, 会直接向上抛出, 
                异常类型由具体 ErrorHandler 决定. 
        """
        while True:
            try:
                keys = self._selector.select(timeout)
            except Exception as cause:
                exc = CycleSelectError("Select调用失败", cause=cause)
                if not self._handle_error(exc, None):
                    return

            if self._pop_notifier_key(keys):
                for action, target, *args in self._notifier:
                    if not self._handle_notifier(action, target, *args):
                        return

            for key, events in keys:
                target = key.fileobj
                if self._context_manager.is_invalid(target):
                    self._context_manager.mark_changed(target)
                    continue
                if events & selectors.EVENT_READ:
                    if not self._handle_read(target):
                        return
                if events & selectors.EVENT_WRITE:
                    if not self._handle_write(target):
                        return

            for target in self._context_manager.drain_changed():
                if not self._update_selector(target):
                    return
                self._context_manager.discard_stale(target)

            if run_once:
                return

    def watch(
        self,
        target: FileDescriptorLike,
        *,
        extra: Any = None,
        on_read: EventHandler | None = None,
        on_write: EventHandler | None = None,
        on_error: ErrorHandler | None = None,
    ) -> None:
        """
        注册资源监听请求. 

        该操作不会立即生效, 而是通过消息机制发送注册请求, 
        由事件调度器在后续周期中处理并应用. 

        若目标资源已注册, 视为更新监听配置, 
        支持重复调用无副作用. 

        Args:
            target: 要监听的文件描述符对象. 
            extra: 附加上下文数据, 会传递给事件处理器. 
            on_read: 可选的读事件处理器. 
            on_write: 可选的写事件处理器. 
            on_error: 可选的错误处理器, 用于覆盖默认处理逻辑. 
        """
        self._notifier.notify(("watch", target, extra, on_read, on_write, on_error))

    def unwatch(self, target: FileDescriptorLike) -> None:
        """
        注销资源监听请求. 

        该操作不会立即移除监听器, 而是通过消息机制发送注销请求, 
        由事件调度器在后续周期中处理. 

        若目标资源未注册则无副作用; 
        若资源正在执行操作, 将在当前操作完成后延迟注销. 

        Args:
            target: 要取消监听的文件描述符对象. 
        """
        self._notifier.notify(("unwatch", target))

    def close(self) -> None:
        """
        关闭事件循环调度器

        终止后续事件调度流程, 并释放内部资源. 
        """
        if self.closed:
            return
        self.closed = True
        with contextlib.suppress(Exception):
            self._notifier.notify(("shutdown",))
        with contextlib.suppress(Exception):
            for target in self._selector.get_map():
                self._selector.unregister(target)
        with contextlib.suppress(Exception):
            self._notifier.close()
        with contextlib.suppress(Exception):
            self._selector.close()

    def _pop_notifier_key(
        self, items: list[tuple[selectors.SelectorKey, EventMask]]
    ) -> tuple | None:
        """从事件列表中提取 notifier 对应的事件项. """
        for i in range(len(items)):
            if items[i][0].fileobj is self._notifier:
                return items.pop(i)
        return None

    def _handle_notifier(
        self, action: str, target: FileDescriptorLike, *args: Any
    ) -> bool:
        """执行 notifier 的调度命令. """
        match action, target, *args:
            case "watch", target, extra, read_handler, write_handler, error_handler:
                self._context_manager.create(
                    target, extra, read_handler, write_handler, error_handler
                )
            case "unwatch", target:
                self._context_manager.remove(target)
            case "read_done", target, resume:
                self._context_manager.pending_read(target, False)
                if not resume:
                    self._context_manager.read_handler(target, None)
            case "write_done", target, resume:
                self._context_manager.pending_write(target, False)
                if not resume:
                    self._context_manager.write_handler(target, None)
            case "shutdown":
                return False
        return True

    def _handle_read(self, target: FileDescriptorLike) -> bool:
        """处理已准备就绪的读事件, 触发关联处理器. """
        handler = self._context_manager.read_handler(target)
        pending = self._context_manager.pending_read(target)

        if handler is None or pending:
            return True

        pending = True

        extra = self._context_manager.extra(target)
        done = partial(self._done_callback, target, "read_done")
        try:
            result = handler(target, extra, done)
        except Exception as cause:
            exc = CycleReadHandlerError("ReadHandler失败", cause=cause)
            return self._handle_error(exc, target)

        if isinstance(result, bool):
            pending = False
            if not result:
                handler = None
        elif isinstance(result, Future):
            result.add_done_callback(
                lambda f: done(not f.cancelled() and not f.exception())
            )

        self._context_manager.read_handler(target, handler)
        self._context_manager.pending_read(target, pending)
        return True

    def _handle_write(self, target: FileDescriptorLike) -> bool:
        """处理已准备就绪的写事件, 触发关联处理器. """
        handler = self._context_manager.write_handler(target)
        pending = self._context_manager.pending_write(target)

        if handler is None or pending:
            return True

        pending = True

        extra = self._context_manager.extra(target)
        done = partial(self._done_callback, target, "write_done")
        try:
            result = handler(target, extra, done)
        except Exception as cause:
            exc = CycleWriteHandlerError("WriteHandler失败", cause=cause)
            return self._handle_error(exc, target)

        if isinstance(result, bool):
            pending = False
            if not result:
                handler = None
        elif isinstance(result, Future):
            result.add_done_callback(
                lambda f: done(not f.cancelled() and not f.exception())
            )

        self._context_manager.write_handler(target, handler)
        self._context_manager.pending_write(target, pending)
        return True

    def _handle_error(
        self,
        exc: EventCycleError,
        target: FileDescriptorLike | None,
        *,
        on_error: ErrorHandler | None = None,
    ) -> bool:
        """根据异常处理策略执行错误处理流程. """
        if on_error is not None:
            return on_error(exc, self._context_manager, target)

        if target is not None:
            error_handler = self._context_manager.error_handler(target)
            if error_handler is not None:
                return error_handler(exc, self._context_manager, target)

        if self.error_handler is not None:
            return self.error_handler(exc, self._context_manager, target)

        return self._default_error_handler(exc, self._context_manager, target)

    def _default_error_handler(
        self,
        exc: EventCycleError,
        manager: ContextManager,
        target: FileDescriptorLike | None,
    ) -> bool:
        """未定义处理器时抛出异常作为兜底处理. """
        raise exc from exc.cause

    def _done_callback(
        self,
        target: FileDescriptorLike,
        action: Literal["read_done", "write_done"],
        resume: bool = True,
    ) -> None:
        """将操作完成信号注入 notifier 等待调度处理. """
        if self.closed:
            return
        self._notifier.notify((action, target, resume))

    def _update_selector(self, target: FileDescriptorLike) -> bool:
        """根据资源状态更新 selector 的注册项. """
        is_registered = target in self._selector.get_map()
        is_invalid = self._context_manager.is_invalid(target)
        events = self._context_manager.events(target)

        try:
            if is_invalid or events == 0:
                if is_registered:
                    self._selector.unregister(target)
            elif is_registered:
                self._selector.modify(target, events)
            else:
                self._selector.register(target, events)
        except OSError as cause:
            exc = CycleSelectError("Selector更新失败", cause=cause)
            return self._handle_error(exc, target)
        return True
