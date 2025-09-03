"""
定义事件调度器使用的异常体系, 支持错误链追踪与分层处理机制.

异常层级结构如下:
    - EventCycleError: 所有异常的统一基类, 支持嵌套链式追踪.
        - CycleInternalError: 系统级错误, 非用户代码导致.
            - CycleSelectError: 与 selector 调用相关的 I/O 异常.
        - CycleHandlerError: 事件处理器执行时发生的用户代码异常.
            - CycleReadHandlerError: 读取事件回调出错.
            - CycleWriteHandlerError: 写入事件回调出错.

主要用途:
    - 为 EventCycle 提供统一的异常捕获与分类处理能力;
    - 支持基于异常类型的容错回调与中断机制;
    - 保留原始异常信息以辅助调试与追溯.
"""

from __future__ import annotations

from typing import Any


class EventCycleError(Exception):
    """
    所有 EventCycle 异常的基类,具备错误链追踪能力.

    参数:
    - `*args`: 异常消息内容;
    - `cause`: 可选的原始异常,用于记录异常链(自动赋值给 `__cause__`).

    用途:
    - 提供统一的异常捕获接口;
    - 支持错误回溯与分层处理;
    """

    def __init__(self, *args: Any, cause: Exception | None = None) -> None:
        super().__init__(*args)
        self.cause: Exception | None = cause
        self.__cause__ = cause


class CycleInternalError(EventCycleError):
    """
    事件调度器内部错误基类(非用户回调导致).

    通常出现在 select 调用失败/selector 注册异常等系统级故障.
    适用于自动终止事件循环或触发系统级恢复流程.
    """


class CycleSelectError(CycleInternalError):
    """
    Selector 调用相关异常.

    说明:
    - 包括 `select()`/`register()`/`modify()`/`unregister()` 等失败;
    - 通常由底层 OSError 或 I/O 异常引起;
    - 属于严重系统错误,建议直接终止事件循环.
    """


class CycleHandlerError(EventCycleError):
    """
    事件处理器相关错误的基类.

    指由事件处理回调引发的异常,通常由用户代码抛出.
    Dispatcher 会尝试使用 ErrorHandler 进行容错处理.
    """


class CycleReadHandlerError(CycleHandlerError):
    """
    读取事件处理器的异常.

    说明:
    - 在 `read_handler()` 执行过程中抛出;
    - Dispatcher 会尝试调用指定或默认的 ErrorHandler;
    """


class CycleWriteHandlerError(CycleHandlerError):
    """
    写入事件处理器的异常.

    说明:
    - 在 `write_handler()` 执行过程中抛出;
    - Dispatcher 会尝试容错或中断事件循环;
    """
