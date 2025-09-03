"""
通用装饰器基类

该模块提供了一个可继承的装饰器基类, 可同时用于同步和异步函数.
它支持**有参**和**无参**两种装饰器形式, 并允许分阶段传递装饰器参数(多次调用累积参数).

核心机制:
    - **阶段 1(参数收集阶段)**:
        如果第一个位置参数不是可识别的函数/方法类型(见 FUNC_TYPES),
        则认为这是在传递装饰器参数, 返回一个新的基类实例以继续收集参数.
    - **阶段 2(绑定函数阶段)**:
        如果第一个位置参数是函数/方法, 则认为这是最终的被装饰对象,
        创建子类实例并调用其 `__init__` 注册装饰器参数, 然后返回包装器函数.

特点:
    - 同时支持同步和异步函数(自动选择 `wrapper` 或 `async_wrapper`).
    - 支持多阶段参数传递(可分多次调用设置装饰器参数).
    - 子类只需实现 `wrapper` / `async_wrapper` 即可定义装饰逻辑.

使用示例:
    ```python
    class ExampleDecorator(Decorator):
        def __init__(self, arg1=1, arg2=2, *, kwarg1=None, kwarg2=None):
            # 这里是注册装饰器参数的地方
            # 不调用 super().__init__ 也能在 self.kwargs 中获取到全部装饰器参数
            super().__init__(1, 2, kwarg1=None, kwarg2=None)
            self.arg1 = arg1
            self.arg2 = arg2
            self.kwarg1 = kwarg1
            self.kwarg2 = kwarg2

        def wrapper(self, *args, **kwargs):
            print("before")
            result = super().wrapper(*args, **kwargs)
            print("after")
            return result

        async def async_wrapper(self, *args, **kwargs):
            print("before async")
            result = await super().async_wrapper(*args, **kwargs)
            print("after async")
            return result

    @ExampleDecorator
    def foo():
        pass

    @ExampleDecorator(1, 2)
    def bar():
        pass

    # 分阶段传参
    deco = ExampleDecorator(arg1=123)
    @deco(arg2=456)
    def baz():
        pass
    @deco(arg2=789)
    def baz2():
        pass
    ```
"""

from __future__ import annotations

import asyncio
import functools
import types
from typing import Any, Callable, Type, final


class Decorator:
    """
    通用装饰器基类.

    属性:
        cls (Type[decorator]): 装饰器类.
        func (Callable[..., Any]): 被装饰的函数对象.
        args (tuple[Any]): 在装饰器参数收集阶段累积的位置参数.
        kwargs (dict[str, Any]): 在装饰器参数收集阶段累积的关键字参数.

    方法:
        __init__(self, ...) -> None:
            初始化装饰器参数, 子类需重写.
        wrapper(self, *args, **kwargs) -> Any:
            同步包装逻辑, 子类需重写.
        async_wrapper(self, *args, **kwargs) -> Any:
            异步包装逻辑, 子类需重写.
    """

    FUNC_TYPES = (
        types.FunctionType,
        types.MethodType,
        types.BuiltinFunctionType,
        types.BuiltinMethodType,
    )

    cls: Type[Decorator]
    func: Callable[..., Any]
    args: tuple[Any]
    kwargs: dict[str, Any]

    @final
    def __new__(cls, *args: Any, **kwargs: Any) -> Decorator:
        self = object.__new__(Decorator)
        self.cls = cls
        self.args = tuple()
        self.kwargs = dict()
        return self.__call__(*args, **kwargs)

    @final
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if not args or not isinstance(args[0], self.FUNC_TYPES):
            next_self = object.__new__(Decorator)
            next_self.cls = self.cls
            next_self.args = (*self.args, *args)
            next_self.kwargs = {**self.kwargs, **kwargs}
            return next_self.__call__

        final_self = object.__new__(self.cls)
        final_self.cls = self.cls
        final_self.func = args[0]
        final_self.args = (*self.args, *args[1:])
        final_self.kwargs = {**self.kwargs, **kwargs}
        final_self.__init__(*final_self.args, **final_self.kwargs)
        return self._get_wrapper(final_self)

    @final
    def _get_wrapper(self, final_self: Decorator) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(final_self.func):

            @functools.wraps(final_self.func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await final_self.async_wrapper(*args, **kwargs)

            return async_wrapper

        @functools.wraps(final_self.func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return final_self.wrapper(*args, **kwargs)

        return wrapper

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        装饰器初始化方法.

        这里是注册装饰器参数的地方:
            - 在绑定函数阶段(阶段 2)调用.
            - `args` / `kwargs` 包含了在参数收集阶段传入的所有装饰器参数.
            - 子类可在此方法中解析并保存装饰器参数到实例属性.

        默认实现为空, 不做任何处理.
        """
        pass

    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        包装被装饰的函数以进行同步执行.

        当被装饰的函数是同步函数时调用此方法.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的结果.

        异常:
            Exception: 如果执行失败, 则抛出引发的异常.
        """
        return self.func(*args, **kwargs)

    async def async_wrapper(self, *args: Any, **kwargs: Any) -> Any:
        """
        包装被装饰的函数以进行异步执行.

        当被装饰的函数是异步函数时调用此方法.

        参数:
            *args (Any): 传递给被装饰函数的位置参数.
            **kwargs (Any): 传递给被装饰函数的关键字参数.

        返回:
            Any: 被装饰函数的结果.

        异常:
            Exception: 如果执行失败, 则抛出引发的异常.
        """
        return await self.func(*args, **kwargs)
