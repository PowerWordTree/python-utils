"""
事件循环上下文管理模块.

模块提供轻量级上下文容器机制, 支持处理器配置/状态标志维护及事件掩码生成, 
重要字段更新自动触发变更标记机制, 为调度器提供高效的状态更新管理能力. 

模块结构:
    - ContextManager: 全局资源上下文管理器, 负责上下文存储与变更管理
    - EventContext: 单资源上下文容器, 存储具体资源的处理状态及回调处理器
"""

from __future__ import annotations

import copy
import selectors
from dataclasses import dataclass, field
from types import EllipsisType
from typing import Any, Iterable

from pwt.utils.event_cycle.interfaces import (
    ErrorHandler,
    EventHandler,
    EventMask,
    FileDescriptorLike,
)


@dataclass
class EventContext:
    target: FileDescriptorLike
    extra: Any = None
    read_handler: EventHandler | None = None
    write_handler: EventHandler | None = None
    error_handler: ErrorHandler | None = None
    pending_read: bool = field(default=False, init=False)
    pending_write: bool = field(default=False, init=False)
    stale: bool = field(default=False, init=False)


class ContextManager:
    """
    事件循环中的资源状态管理器. 

    该类用于集中维护参与调度的资源上下文, 
    支持处理器配置/状态标志读写/事件掩码生成与失效管理. 

    更新以下字段时自动触发变更标记机制, 为调度器提供高效的状态更新管理能力: 
        - `read_handler`
        - `write_handler`
        - `pending_read`
        - `pending_write`
        - `stale`
    """

    def __init__(self) -> None:
        """构造空的上下文集合与变更标记容器"""
        self._contexts: dict[FileDescriptorLike, EventContext] = {}
        self._changed: set[FileDescriptorLike] = set()

    def _ensure(self, target: FileDescriptorLike) -> EventContext:
        """获取指定的上下文实例, 不存在时自动创建并标记为废弃"""
        context = self._contexts.get(target)
        if context is None:
            context = EventContext(target)
            context.stale = True  # 无效的Context标记
            self._contexts[target] = context
            self.mark_changed(target)
        return context

    ##### Changed #####

    def mark_changed(self, target: FileDescriptorLike) -> None:
        """
        指定的资源触发变更标记机制, 为调度器提供高效的状态更新管理能力. 

        参数:
            target: 指定的资源
        """
        self._changed.add(target)

    def drain_changed(self) -> set[FileDescriptorLike]:
        """
        提取并清空全部触发变更标记的资源. 

        返回:
            全部触发变更标记的资源集合. 
        """
        changed = self._changed
        self._changed = set()
        return changed

    ##### Context #####

    def create(
        self,
        target: FileDescriptorLike,
        extra: Any = None,
        read_handler: EventHandler | None = None,
        write_handler: EventHandler | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        """
        创建或更新资源标识符的上下文信息. 

        调用后将自动触发变更标记机制, 为调度器提供高效的状态更新管理能力. 

        参数:
            target: 资源标识符. 
            extra: 附加信息, 用于调度器扩展用途. 
            read_handler: 读取事件处理器. 
            write_handler: 写入事件处理器. 
            error_handler: 错误事件处理器. 
        """
        context = self._ensure(target)
        context.extra = extra
        context.read_handler = read_handler
        context.write_handler = write_handler
        context.error_handler = error_handler
        context.stale = False
        self.mark_changed(target)

    def remove(self, target: FileDescriptorLike) -> None:
        """
        标记资源标识符的上下文信息为废弃. 

        调用后将自动触发变更标记机制, 为调度器提供高效的状态更新管理能力. 

        参数:
            target: 资源标识符. 

        返回:
            对应资源的上下文对象. 
        """
        context = self._ensure(target)
        context.stale = True
        self.mark_changed(target)

    def modify(
        self,
        target: FileDescriptorLike,
        extra: Any | EllipsisType = ...,
        read_handler: EventHandler | None | EllipsisType = ...,
        write_handler: EventHandler | None | EllipsisType = ...,
        error_handler: ErrorHandler | None | EllipsisType = ...,
    ) -> None:
        """
        更新资源标识符的上下文信息, 支持部分更新. 

        调用后将自动触发变更标记机制, 为调度器提供高效的状态更新管理能力. 

        参数:
            target: 资源标识符. 
            extra: 附加信息, 用于调度器扩展用途. 
            read_handler: 读取事件处理器. 
            write_handler: 写入事件处理器. 
            error_handler: 错误事件处理器. 
        """
        context = self._ensure(target)
        if extra is not ...:
            context.extra = extra
        if read_handler is not ...:
            context.read_handler = read_handler
        if write_handler is not ...:
            context.write_handler = write_handler
        if error_handler is not ...:
            context.error_handler = error_handler
        self.mark_changed(target)

    def inspect(self, target: FileDescriptorLike) -> EventContext | None:
        """
        返回目标资源上下文的副本. 

        参数:
            target: 资源对应的文件描述符. 

        返回:
            对应的上下文副本对象, 若资源未注册则返回 None. 
        """
        return copy.copy(self._contexts.get(target))

    def targets(self) -> Iterable[FileDescriptorLike]:
        """
        返回所有已注册资源的标识符集合视图, 用于遍历. 

        返回:
            可迭代的资源标识符集合. 
        """
        return self._contexts.keys()

    def has(self, target: FileDescriptorLike) -> bool:
        """
        检查指定资源是否已注册. 

        参数:
            target: 资源对应的文件描述符. 

        返回:
            若资源已存在于上下文集合中, 则返回 True; 否则返回 False. 
        """
        return target in self._contexts

    def is_invalid(self, target: FileDescriptorLike) -> bool:
        """
        判断指定资源是否未注册或已废弃. 

        参数:
            target: 资源对应的文件描述符. 

        返回:
            若资源未注册或已被标记为失效, 则返回 True. 
        """
        context = self._contexts.get(target)
        return context is None or context.stale

    def events(self, target: FileDescriptorLike) -> EventMask:
        """
        计算并返回目标资源的事件掩码. 

        仅在对应处理器存在, 且资源未标记为使用中时, 
        掩码中才包含可读或可写事件位. 

        参数:
            target: 资源对应的文件描述符. 

        返回:
            表示资源可读/可写状态的事件掩码. 
        """
        context = self._contexts.get(target)
        if context is None:
            return 0
        events = 0
        if context.read_handler and not context.pending_read:
            events |= selectors.EVENT_READ
        if context.write_handler and not context.pending_write:
            events |= selectors.EVENT_WRITE
        return events

    def discard_stale(self, target: FileDescriptorLike) -> None:
        """
        若目标资源已失效且无挂起读/写事件, 则将其移出上下文集合. 

        参数:
            target: 资源对应的文件描述符. 
        """
        context = self._contexts.get(target)
        if context is not None:
            if context.stale:
                if not context.pending_read and not context.pending_write:
                    self._contexts.pop(target, None)

    ##### Getting & Setting #####

    def extra(
        self,
        target: FileDescriptorLike,
        value: Any | None | EllipsisType = ...,
    ) -> Any | None:
        """
        获取或设置资源的附加信息. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的附加信息, 或使用 `...` 表示不修改. 

        返回:
            当前附加信息. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.extra = value
        return context.extra

    def read_handler(
        self,
        target: FileDescriptorLike,
        value: EventHandler | None | EllipsisType = ...,
    ) -> EventHandler | None:
        """
        获取或设置读取事件处理器. 

        设置时自动将资源加入变更集合 `changed`. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的处理器, 或使用 `...` 表示不修改. 

        返回:
            当前绑定的读取处理器. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.read_handler = value
            self.mark_changed(target)
        return context.read_handler

    def write_handler(
        self,
        target: FileDescriptorLike,
        value: EventHandler | None | EllipsisType = ...,
    ) -> EventHandler | None:
        """
        获取或设置写入事件处理器. 

        设置时自动将资源加入变更集合 `changed`. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的处理器, 或使用 `...` 表示不修改. 

        返回:
            当前绑定的写入处理器. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.write_handler = value
            self.mark_changed(target)
        return context.write_handler

    def error_handler(
        self,
        target: FileDescriptorLike,
        value: ErrorHandler | None | EllipsisType = ...,
    ) -> ErrorHandler | None:
        """
        获取或设置错误处理器. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的处理器, 或使用 `...` 表示不修改. 

        返回:
            当前绑定的错误处理器. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.error_handler = value
        return context.error_handler

    def pending_read(
        self,
        target: FileDescriptorLike,
        value: bool | EllipsisType = ...,
    ) -> bool | None:
        """
        获取或设置挂起读取标志. 

        设置时自动将资源加入变更集合 `changed`. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的挂起标志, 或使用 `...` 表示不修改. 

        返回:
            当前挂起读取标志状态. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.pending_read = value
            self.mark_changed(target)
        return context.pending_read

    def pending_write(
        self,
        target: FileDescriptorLike,
        value: bool | EllipsisType = ...,
    ) -> bool | None:
        """
        获取或设置挂起写入标志. 

        设置时自动将资源加入变更集合 `changed`. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的挂起标志, 或使用 `...` 表示不修改. 

        返回:
            当前挂起写入标志状态. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.pending_write = value
            self.mark_changed(target)
        return context.pending_write

    def stale(
        self,
        target: FileDescriptorLike,
        value: bool | EllipsisType = ...,
    ) -> bool | None:
        """
        获取或设置资源失效标志. 

        设置时自动将资源加入变更集合 `changed`. 

        参数:
            target: 资源对应的文件描述符. 
            value: 新的失效标志, 或使用 `...` 表示不修改. 

        返回:
            当前失效标志状态. 
        """
        context = self._ensure(target)
        if value is not ...:
            context.stale = value
            self.mark_changed(target)
        return context.stale
