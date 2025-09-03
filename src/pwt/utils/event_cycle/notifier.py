"""
事件循环通知器模块

本模块提供事件循环中的异步调度驱动机制, 封装为 Notifier 抽象类, 并通过管道或 socketpair

实现跨平台兼容性. 所有调度指令以队列形式存储, 由内部 `_wakeup()` 实现事件唤醒.
适用于基于 selector 的事件循环系统.

核心组成:
    - Notifier: 通用通知器接口, 定义事件队列与唤醒行为;
    - PipeNotifier: 使用 Unix 管道实现, 适合类 Unix 系统;
    - SocketNotifier: 使用 socketpair 实现, 适用于 Windows;
    - create_notifier(): 根据平台自动创建合适的通知器实例.
"""

from __future__ import annotations

import contextlib
import os
import queue
import socket
import sys
from abc import ABC, abstractmethod
from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class Notifier(ABC, Generic[T]):
    """
    通用通知器抽象类, 用于驱动 selector 唤醒逻辑.

    所有调度请求封装为队列项, 由子类负责实现跨平台的 `_wakeup()` 行为.
    每次触发唤醒后, 事件循环会调用 `__iter__` 消费所有待处理项.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[T] = queue.Queue()

    def __iter__(self) -> Iterator[T]:
        self._drain()
        while True:
            try:
                yield self._queue.get_nowait()
            except queue.Empty:
                break

    def notify(self, item: T) -> None:
        self._queue.put(item)
        self._wakeup()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    @abstractmethod
    def fileno(self) -> int: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def _wakeup(self) -> None: ...

    @abstractmethod
    def _drain(self) -> None: ...


class PipeNotifier(Notifier):
    """
    基于 Unix 管道实现的通知器.

    通过写入管道触发 selector 唤醒, 并在读取端 drain 数据以重置状态.
    管道为非阻塞模式, 适用于大多数类 Unix 平台.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r_fd, self._w_fd = os.pipe()
        self._r_file = os.fdopen(self._r_fd, "rb", buffering=0)

    def fileno(self) -> int:
        return self._r_file.fileno()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._r_file.close()
        with contextlib.suppress(Exception):
            os.close(self._w_fd)

    def _wakeup(self) -> None:
        with contextlib.suppress(OSError):
            os.write(self._w_fd, b"x")

    def _drain(self) -> None:
        with contextlib.suppress(BlockingIOError):
            while self._r_file.read(1024):
                pass


class SocketNotifier(Notifier):
    """
    基于 socketpair 实现的通知器, 适用于不支持管道的系统(如 Windows).

    通过写 socket 发送唤醒字节, 读取端被 selector 监听以驱动事件处理.
    所用 socket 为非阻塞模式.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r_sock, self._w_sock = socket.socketpair()
        self._r_sock.setblocking(False)

    def fileno(self) -> int:
        return self._r_sock.fileno()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._r_sock.close()
        with contextlib.suppress(Exception):
            self._w_sock.close()

    def _wakeup(self) -> None:
        with contextlib.suppress(OSError):
            self._w_sock.send(b"x")

    def _drain(self) -> None:
        with contextlib.suppress(BlockingIOError):
            while self._r_sock.recv(1024):
                pass


def create_notifier() -> Notifier:
    """
    自动创建合适的通知器实例, 根据平台选择实现.

    - Windows ➜ 使用 SocketNotifier;
    - 其他平台 ➜ 使用 PipeNotifier.

    推荐用于事件循环初始化时作为默认通知机制.
    """
    if sys.platform == "win32":
        return SocketNotifier()
    return PipeNotifier()
