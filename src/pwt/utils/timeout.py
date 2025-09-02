"""
超时管理装饰器

模块提供了一个装饰器, 用于为函数添加超时控制功能.
该模块定义了一个 `Timeout` 类, 它继承自 `Decorator` 类,
并实现了 `wrapper` 和 `async_wrapper` 方法, 分别用于同步和异步函数的超时控制.

功能特性:
    - 支持同步和异步函数的超时控制.
    - 可以指定超时时间, 单位为秒.
    - 可以使用自定义的线程池执行器.

使用方法:
    如果未指定超时时间, 则函数不会有超时限制.
    如果未指定线程池执行器, 则会使用临时的线程池执行器.

    ```python
    # 导入 `Timeout` 类
    from pwt.ddns_guard.utils.timeout import Timeout
    import time

     # 使用 `Timeout` 装饰需要添加超时控制的函数
    @Timeout(timeout=3)
    def sync_function():
        time.sleep(5)
        return "Function completed"

    @Timeout(timeout=3)
    async def async_function():
        await asyncio.sleep(5)
        return "Function completed"

    # 调用被装饰的函数, 如果超时则抛出 `TimeoutError` 或 `asyncio.TimeoutError`
    try:
        result = sync_function()
        print(result)
    except TimeoutError:
        print("Function timed out")
    except Exception:
        print("Other exception")

    try:
        result = asyncio.run(async_function())
        print(result)
    except asyncio.TimeoutError:
        print("Function timed out")
    except Exception:
        print("Other exception")
    ```
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Self, override

from pwt.utils.decorator import Decorator


class Timeout(Decorator):
    """
    超时控制装饰器

    支持同步函数和异步函数.

    属性:
        func (Callable[..., Any]): 被装饰的函数.
        timeout (float | None): 超时时间, 单位为秒.
        executor (ThreadPoolExecutor | None): 线程池执行器.

    方法:
        wrapper(*args: Any, **kwargs: Any) -> Any: 同步调用的包装方法.
        async_wrapper(*args: Any, **kwargs: Any) -> Any: 异步调用的包装方法.
    """

    @override
    def __init__(
        self,
        func: Callable[..., Any] = Self,
        /,
        *,
        timeout: float | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        """
        初始化 `Timeout` 装饰器.

        参数:
            func (Callable[..., Any], optional): 被装饰的函数, 默认用 Self 占位.
            timeout (float | None, optional): 超时时间, 单位为秒, 默认为 `None`.
            executor (ThreadPoolExecutor | None, optional): 线程池执行器. 默认为 `None`.
        """
        super().__init__(func, timeout=timeout, executor=executor)
        self.func = func
        self.timeout = timeout
        self.executor = executor

    @override
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        同步函数的包装方法.

        用于执行被装饰的同步函数并处理超时.
        如果提供了线程池执行器, 则使用该执行器提交任务并等待结果.
        如果未提供线程池执行器, 则创建一个临时的线程池执行器并提交任务.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的返回值.

        异常:
            CancelledError: 如果函数执行被打断.
            TimeoutError: 如果函数执行时间超过指定的超时时间.
            Exception: 如果执行失败, 则抛出引发的异常.
        """
        if self.timeout is None or self.timeout <= 0:
            return self.func(*args, **kwargs)
        if self.executor:
            future = self.executor.submit(self.func, *args, **kwargs)
            return future.result(timeout=self.timeout)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.func, *args, **kwargs)
            return future.result(timeout=self.timeout)

    @override
    async def async_wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        异步函数的包装方法.

        用于执行被装饰的异步函数并处理超时.
        使用 `asyncio.wait_for` 来等待异步函数的完成,
        并在超时时间内未完成时抛出 `asyncio.TimeoutError`.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的返回值.

        异常:
            asyncio.TimeoutError: 如果函数执行时间超过指定的超时时间.
            Exception: 如果执行失败, 则抛出引发的异常.
        """
        if self.timeout is None or self.timeout <= 0:
            return await self.func(*args, **kwargs)
        return await asyncio.wait_for(self.func(*args, **kwargs), timeout=self.timeout)
