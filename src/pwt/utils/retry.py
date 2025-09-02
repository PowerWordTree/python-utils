"""
重试装饰器

该模块提供了重试装饰器和相关工具函数,用于在函数执行后根据条件自动重试.

主要功能:
    - 提供了 `Retry` 装饰器,用于装饰需要重试的函数.
    - 支持同步和异步函数的重试.
    - 提供了多种重试策略,如固定间隔/指数退避等.
    - 支持根据异常类型/返回值等条件判断是否重试.

模块结构:
    - RetryState: 重试状态类,用于存储重试操作的相关信息.
    - Retry: 重试装饰器类,用于执行重试操作.
    - SimpleRetry: 简单重试装饰器类,继承自 Retry.
    - AdvancedRetry: 高级重试装饰器类,继承自 Retry.
    - exponential_backoff_interval: 间隔函数构造器,用于生成指数退避间隔函数.
    - fixd_interval: 间隔函数构造器,用于生成固定间隔函数.
    - retries_retryable: 可重试函数构造器,用于生成根据重试次数判断是否可重试的函数.
    - exception_retryable: 可重试函数构造器,用于生成根据异常类型判断是否可重试的函数.
    - results_retryable: 可重试函数构造器,用于生成根据返回值判断是否可重试的函数.
    - fixd_retryable: 可重试函数构造器,用于生成根据固定条件判断是否可重试的函数.
    - all_retryable: 可重试函数构造器,用于生成根据多个条件判断是否可重试的函数,全部条件满足就可重试.
    - any_retryable: 可重试函数构造器,用于生成根据多个条件判断是否可重试的函数,只要有一个条件满足就可重试.

使用方法:
    SimpleRetry,使用简单,功能固定. AdvancedRetry,退避指数间隔,相对复杂.
    Retry,最灵活,但使用复杂.
    所有以 `interval` 结尾的函数, 都可以传递给 `Retry` 的 `interval` 参数.
    所有以 `retryable` 结尾的函数, 都可以传递给 `Retry` 的 `retryable` 参数.

    ```python
    from pwt.utils.retry import SimpleRetry, AdvancedRetry

    # 使用 `SimpleRetry` 装饰器进行重试
    @SimpleRetry(delay=1, retries=3, exceptions=[ValueError])
    def my_function():
        # 可能会抛出 ValueError 的代码
        pass

    # 使用 `AdvancedRetry` 装饰器进行重试
    @AdvancedRetry(factor=2, maximum=32, jitter=True, retries=5, exceptions=[TypeError])
    def my_async_function():
        # 可能会抛出 TypeError 的异步代码
        pass

    # 使用 `Retry` 装饰器进行重试
    @Retry(
        interval=exponential_backoff_interval(factor=1.8, jitter=True),
        retryable=all_retryable(
            retries_retryable(5),
            any_retryable(
                results_retryable(None, "", [], {}), exception_retryable(TypeError)
            ),
        ),
    )
    def my_async_function():
        # 可能会抛出 TypeError 的异步代码
        pass
    ```
"""

import asyncio
import random
from time import sleep
from typing import Any, Callable, Iterable, Self, Type, override

from pwt.utils.decorator import Decorator


class RetryState:
    """
    重试状态类

    用于存储重试操作的相关信息.

    属性:
        func (Callable[..., Any]): 要重试的函数.
        args (tuple[Any]): 传递给函数的位置参数.
        kwargs (dict[str, Any]): 传递给函数的关键字参数.
        attempts (int): 重试次数.
        delay (float): 延迟时间.
        result (Any): 执行结果.
        exception (Exception | None): 异常信息.
    """

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        初始化 `RetryState` 实例

        参数:
            func (Callable[..., Any]): 要重试的函数.
            *args (Any): 传递给函数的位置参数.
            **kwargs (Any): 传递给函数的关键字参数.
        """
        self.func: Callable[..., Any] = func  # 要重试的函数
        self.args: tuple[Any] = args  # 传递给函数的参数
        self.kwargs: dict[str, Any] = kwargs  # 传递给函数的关键字参数
        self.attempts: int = 0  # 重试次数
        self.delay: float = 0  # 延迟时间
        self.result: Any = None  # 执行结果
        self.exception: Exception | None = None  # 异常信息

    def __str__(self) -> str:
        """
        返回重试状态的字符串表示
        """
        return (
            f"attempts: {self.attempts}, delay: {round(self.delay, 3)}, "
            f"result: {_truncate_middle(self.result, 150)}, "
            f"exception: {repr(self.exception)}, "
            f"func: {self.func.__name__}, args: {self.args}, kwargs: {self.kwargs}"
        )


class Retry(Decorator):
    """
    重试装饰器类

    用于执行重试操作, 继承自 `Decorator` 类.

    属性:
        func (Callable[..., Any]): 被装饰的函数.
        kwds (dict[str, Any]): 传递给装饰器的参数.

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
        interval: Callable[[RetryState], float],
        retryable: Callable[[RetryState], bool],
    ) -> None:
        """
        初始化 `Retry` 实例.

        参数:
            func (Callable[..., Any]): 要重试的函数, 用 `Self` 占位.
            interval (Callable[[RetryState], float]): 计算延迟时间的函数.
            retryable (Callable[[RetryState], bool]): 判断是否可重试的函数.
        """
        super().__init__(func, interval=interval, retryable=retryable)
        self.func = func
        self.interval = interval
        self.retryable = retryable

    @override
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        同步函数的包装方法

        该方法会在每次调用被装饰的函数后检查是否需要重试.
        如果需要重试, 会等待指定时间再次调用被装饰的函数.
        直到不满足重试条件, 输出结果或抛出异常.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的返回值.

        异常:
            Exception: 如果重试失败, 则抛出最后一次捕获的异常.
        """
        state = RetryState(self.func, *args, **kwargs)
        while True:
            state.result = state.exception = None
            try:
                state.result = self.func(*args, **kwargs)
            except Exception as ex:
                state.exception = ex
            if not self.retryable(state):
                if state.exception:
                    raise state.exception
                return state.result
            state.attempts += 1
            state.delay = self.interval(state)
            sleep(state.delay)

    # TODO: 是否能输出debug日志?
    @override
    async def async_wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        异步函数的包装方法.

        该方法会在每次调用被装饰的函数后检查是否需要重试.
        如果需要重试, 会等待指定时间再次调用被装饰的函数.
        直到不满足重试条件, 输出结果或抛出异常.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的返回值.

        异常:
            Exception: 如果重试失败, 则抛出最后一次捕获的异常.
        """
        state = RetryState(self.func, *args, **kwargs)
        while True:
            state.result = state.exception = None
            # log_utils.debug(f"Retry - 执行 - {state}")
            try:
                state.result = await self.func(*args, **kwargs)
            except Exception as ex:
                state.exception = ex
            if not self.retryable(state):
                # log_utils.debug(f"Retry - 结束 - {state}")
                if state.exception:
                    raise state.exception
                return state.result
            # log_utils.debug(f"Retry - 失败 - {state}")
            state.attempts += 1
            state.delay = self.interval(state)
            # log_utils.debug(f"Retry - 延迟 - {state}")
            await asyncio.sleep(state.delay)


class SimpleRetry(Retry):
    """
    简单重试装饰器类

    用于执行重试操作, 继承自 `Retry` 类.
    """

    @override
    def __init__(
        self,
        func: Callable[..., Any] = Self,
        /,
        *,
        delay: float = 1,
        retries: int = 3,
        exceptions: Iterable[Type[Exception]] = [Exception],
        results: Iterable[Any] = [],
    ) -> None:
        """
        初始化 `SimpleRetry` 实例.

        参数:
            func (Callable[..., Any]): 要重试的函数, 用 `Self` 占位.
            delay (float, 可选): 重试的延迟时间(秒), 默认为 `1` 秒.
            retries (int, 可选): 重试次数, 默认为 `3` 次.
            exceptions (Iterable[Type[Exception]], 可选): 可重试的异常类型列表, 默认为所有异常.
            results (Iterable[Any], 可选): 可重试的结果列表, 默认为空列表.
        """
        super().__init__(
            func,
            interval=fixd_interval(delay),
            retryable=fixd_retryable(retries, exceptions, results),
        )


class AdvancedRetry(Retry):
    """
    高级重试装饰器类

    用于执行重试操作, 继承自 `Retry` 类.
    """

    @override
    def __init__(
        self,
        func: Callable[..., Any] = Self,
        /,
        *,
        factor: float = 1,
        maximum: float = 64,
        base: int = 2,
        jitter: bool = False,
        retries: int = 3,
        exceptions: Iterable[Type[Exception]] = [Exception],
        results: Iterable[Any] = [],
    ) -> None:
        """
        初始化 `AdvancedRetry` 实例

        参数:
            func (Callable[..., Any]): 要重试的函数, 用 `Self` 占位.
            factor (float, 可选): 因子,用于计算重试间隔时间
            maximum (float, 可选): 最大重试间隔时间
            base (int, 可选): 指数退避的基数
            jitter (bool, 可选): 是否启用抖动,用于在重试间隔时间上添加随机因素.
            retries (int, 可选): 重试次数, 默认为 `3` 次.
            exceptions (Iterable[Type[Exception]], 可选): 可重试的异常类型列表, 默认为所有异常.
            results (Iterable[Any], 可选): 可重试的结果列表, 默认为空列表.
        """
        super().__init__(
            func,
            interval=exponential_backoff_interval(factor, maximum, base, jitter),
            retryable=fixd_retryable(retries, exceptions, results),
        )


def exponential_backoff_interval(
    factor: float = 1, maximum: float = 64, base: int = 2, jitter: bool = False
) -> Callable[[RetryState], float]:
    """
    间隔函数构造器-指数退避间隔

    该函数用于计算每次重试之间的间隔时间.
    间隔时间会随着重试次数的增加而指数级增长, 直到达到最大值.

    参数:
        factor (float): 因子,用于计算重试间隔时间.
        maximum (float): 最大重试间隔时间.
        base (int): 指数退避的基数.
        jitter (bool): 是否启用抖动,用于在重试间隔时间上添加随机因素.

    返回:
        Callable[[RetryState], float]: 一个函数,该函数接受一个 `RetryState` 对象并返回下一次重试的间隔时间.
    """
    return lambda state: _exponential_backoff(
        factor, state.attempts, maximum, base, jitter
    )


def fixd_interval(delay: float) -> Callable[[RetryState], float]:
    """
    间隔函数构造器-固定间隔

    该函数用于生成一个固定间隔的重试间隔函数.
    每次重试之间的间隔时间是固定的, 由 `delay` 参数指定.

    参数:
        delay (float): 重试之间的固定间隔时间(秒).

    返回:
        Callable[[RetryState], float]: 一个函数,该函数接受一个 `RetryState` 对象并返回固定的间隔时间 `delay`.
    """
    return lambda _: delay


def retries_retryable(retries: int) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-重试次数

    该函数用于生成一个可重试函数,该函数根据重试次数判断是否可重试.

    参数:
        retries (int): 重试次数.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    return lambda state: state.attempts < retries


def exception_retryable(*exceptions: Type[Exception]) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-异常类型列表

    该函数用于生成一个可重试函数,该函数根据异常类型判断是否可重试.

    参数:
        exceptions (Type[Exception]): 异常类型列表.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    return lambda state: any(isinstance(state.exception, e) for e in exceptions)


def results_retryable(*results: Any) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-返回值列表

    该函数用于生成一个可重试函数,该函数根据函数的返回值判断是否可重试.

    参数:
        results (Any): 可重试的返回值列表.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    return lambda state: any(state.result == r for r in results)


def fixd_retryable(
    retries: int, exceptions: Iterable[Type[Exception]], results: Iterable[Any]
) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-固定条件

    该函数用于生成一个可重试函数,该函数根据重试次数/异常类型和返回值判断是否可重试.

    参数:
        retries (int): 重试次数.
        exceptions (Iterable[Type[Exception]]): 可重试的异常类型列表.
        results (Iterable[Any]): 可重试的返回值列表.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    retries_func = retries_retryable(retries)
    exception_func = exception_retryable(*exceptions)
    results_func = results_retryable(*results)
    return lambda state: retries_func(state) and (
        exception_func(state) or results_func(state)
    )


def all_retryable(
    *conditions: Callable[[RetryState], bool],
) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-全部条件

    该函数用于生成一个可重试函数,该函数根据多个条件判断是否可重试.

    参数:
        *conditions (Callable[[RetryState], bool]): 可重试函数列表.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    return lambda state: all(func(state) for func in conditions)


def any_retryable(
    *conditions: Callable[[RetryState], bool],
) -> Callable[[RetryState], bool]:
    """
    可重试函数构造器-任意条件

    该函数用于生成一个可重试函数,该函数根据多个条件判断是否可重试.只要有一个条件满足,就认为可重试.

    参数:
        *conditions (Callable[[RetryState], bool]): 可重试函数列表.

    返回:
        Callable[[RetryState], bool]: 一个函数,该函数接受一个 `RetryState` 对象并返回一个布尔值,表示是否可重试.
    """
    return lambda state: any(func(state) for func in conditions)


def _exponential_backoff(
    factor: float, attempts: int, maximum: float, base: int = 2, jitter: bool = False
) -> float:
    """
    计算指数退避值的内部函数.

    该函数用于计算每次重试之间的间隔时间,间隔时间会随着重试次数的增加而指数级增长,
    直到达到最大值.如果启用了抖动,间隔时间会在一定范围内随机化.

    参数:
        factor (float): 因子,用于计算重试间隔时间.
        attempts (int): 重试次数.
        maximum (float): 最大重试间隔时间.
        base (int): 指数退避的基数.
        jitter (bool): 是否启用抖动,用于在重试间隔时间上添加随机因素.

    返回:
        float: 下一次重试的间隔时间.
    """
    delay = min(base**attempts * factor, maximum)
    if jitter:
        delay = random.uniform(attempts * factor, delay)
    return max(delay, 0)


def _truncate_middle(obj: Any, length: int) -> str:
    """
    字符串内部截断

    该函数用于将字符串从中间截断,并在截断处添加省略号.

    参数:
        obj (Any): 要截断的对象,可以是任何类型,但最终会转换为字符串.
        length (int): 截断后的字符串长度.

    返回:
        str: 截断后的字符串, 以 ` ... ` 作为分隔符.

    示例:
        >>> _truncate_middle("abcdefghijkijklmnopqrst", 10)
        'abc ... st'
    """
    if length <= 5:
        return " ... "
    text = str(obj).replace("\n", " ").strip()
    if len(text) > length:
        begin_len = end_len = (length - 5) // 2
        begin_len += (length - 5) % 2
        text = text[:begin_len] + " ... " + text[-end_len:]
    return text
