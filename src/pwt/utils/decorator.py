"""
通用装饰器基类

这个模块提供了一个用于创建装饰器的基类,该装饰器可以用于同步和异步函数.
`Decorator` 类是一个通用的装饰器基类,可以被继承来创建自定义装饰器.
它提供了一种灵活的方式来定义可以接受参数并用于同步和异步函数的装饰器.

核心逻辑:
    如果第一个参数 `func` 被赋值, 则返回装饰器实例.
    如果第一个参数 `func` 未赋值, 则返回包含部分参数的基类实例.

使用方法:
    继承基类后, 可以简单的创建同时支持有参数和无参数的装饰器.

    ```python
    class ExampleDecorator(Decorator):

        def __init__(self, func: Callable[..., Any] = Self, /, *, arg1=...) -> None:
            # arg1=... 替换为装饰器参数, 可以在装饰方法时提示参数和设置默认参数.
            # 不覆盖或者调用父类__init__可以在self.kwds获取到装饰器参数.
            super().__init__(func, arg1=...)
            self.arg1 = ...

        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            ...  # 执行前操作
            result = super().wrapper(*args, **kwargs)
            ...  # 执行后操作
            return result

        @override
        async def async_wrapper(self, *args: Any, **kwargs: Any) -> Any:
            ...  # 执行前操作
            result = await self.func(*args, **kwargs)
            ...  # 执行后操作
            return result

    @ExampleDecorator  # 使用默认参数
    @ExampleDecorator(arg1=...)  # 可以设置装饰器参数
    @ExampleDecorator(arg1=...)(arg2=...)  # 可以分次设置
    def example_func():
        pass

    # 使用模板批量装饰
    template_decorator = ExampleDecorator(arg1=...)  # 构建模板

    @template_decorator
    def aaa_func():
        pass

    @template_decorator(arg2=...)
    def bbb_func():
        pass

    ```
"""

import asyncio
import functools
from typing import Any, Callable, Self, Type, final


class Decorator:
    """
    通用装饰器基类

    属性:
        func (Callable[..., Any]): 被装饰的函数.
        kwds (dict[str, Any]): 传递给装饰器的参数.

    方法:
        wrapper(self, *args: Any, **kwargs: Any) -> Any: 包装被装饰的函数以进行同步执行.
        async_wrapper(self, *args: Any, **kwargs: Any) -> Any: 包装被装饰的函数以进行异步执行.
    """

    @final
    def __new__(cls, func: Callable[..., Any] = Self, /, **kwds: Any) -> "Decorator":
        if func is Self:
            # 子类实例化时,不会执行__init__方法.
            self = object.__new__(Decorator)
            self.__init__(**kwds)
            self._cls = cls
        else:
            self = super().__new__(cls)
            functools.update_wrapper(self, func)
        return self

    def __init__(self, func: Callable[..., Any] = Self, /, **kwds: Any) -> None:
        """
        初始化装饰器.

        参数:
            func (Callable[..., Any]): 被装饰的函数,默认用 `Self` 占位.
            **kwds (Any): 传递给装饰器的参数.
        """
        self.func = func
        self.kwds = kwds
        self._cls: Type[Decorator]

    @final
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        if self.func is Self:
            self.kwds.update(kwds)
            return self._cls(*args, **self.kwds)
        if asyncio.iscoroutinefunction(self.func):
            return self.async_wrapper(*args, **kwds)
        return self.wrapper(*args, **kwds)

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
