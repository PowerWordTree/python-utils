"""
通用装饰器辅助工具 (Decorator)

本模块提供统一的装饰器工厂类, 用于简化装饰器的编写过程. 

核心特性: 
- 使用 `Params` 对象统一收集和传递装饰器参数
- 支持直接传参的简化语法(可能产生歧义时需谨慎使用)
- 支持分阶段传参: 通过多次调用逐步累积参数
- 在参数合并时自动处理关键字参数到位置参数的转换
- 支持 Ellipsis (`...`) 占位符: 跳过特定参数, 保留之前的值
- 同时兼容函数式和类式装饰器
- 保留完整的函数签名 (ParamSpec/TypeVar), 确保 IDE 友好性

参数处理机制: 
- 基于 inspect 模块分析装饰器函数签名
- 建立参数名到位置索引的映射关系
- 在参数合并时自动处理关键字参数到位置参数的转换
- 支持 Ellipsis 占位符实现参数跳过功能

使用示例:
    # 函数式装饰器定义
    @Decorator
    def my_decorator(func, func_args, func_kwargs, prefix="", suffix=""):
        print(f"{prefix}Before{suffix}")
        result = func(*func_args, **func_kwargs)
        print(f"{prefix}After{suffix}")
        return result

    # 无参模式使用
    @my_decorator
    def foo(): ...

    # 有参模式使用
    @my_decorator(prefix=">>>", suffix="<<<")
    def bar(): ...

    # 分阶段传参
    deco = my_decorator(prefix=">>>")
    @deco(suffix="<<<")
    def baz(): ...

    # 使用 Params 显式传参
    params = Params(prefix=">>>", suffix="<<<")
    @my_decorator(params)
    def qux(): ...

    # 使用 Ellipsis 占位符
    @my_decorator(..., suffix="<<<")
    def quux(): ...

    # 类式装饰器定义
    @Decorator
    class MyDecorator:
        def __init__(self, func, prefix="", suffix=""):
            self.func = func
            self.prefix = prefix
            self.suffix = suffix

        def __call__(self, *args, **kwargs):
            print(f"{self.prefix}Before{self.suffix}")
            result = self.func(*args, **kwargs)
            print(f"{self.prefix}After{self.suffix}")
            return result

    # 类式装饰器使用示例
    @MyDecorator("test")
    def foo(): ...

    @MyDecorator("test", prefix=">>> ", suffix=" <<<")
    def bar(): ...

    deco = MyDecorator("test", prefix=">>> ")
    @deco(suffix=" <<<")
    def baz(): ...

    @MyDecorator("test", ..., suffix=" <<<")
    def qux(): ...
"""

from __future__ import annotations

import functools
import inspect
from itertools import zip_longest
from typing import (
    Any,
    Callable,
    Generic,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)

P = ParamSpec("P")
R = TypeVar("R", covariant=True)
DP = ParamSpec("DP")


@runtime_checkable
class DecoratorFunction(Protocol[DP]):
    """
    装饰器函数协议, 定义装饰器函数的标准签名. 

    装饰器函数应接收以下参数: 
    - func: 被装饰的目标函数
    - func_args: 被装饰函数的位置参数
    - func_kwargs: 被装饰函数的关键字参数
    - *args: 装饰器自身的位置参数
    - **kwargs: 装饰器自身的关键字参数

    用途:
        用于类型检查, 确保装饰器函数符合预期的签名格式. 
    """

    def __call__(
        self,
        func: Callable[..., Any],
        func_args: tuple[Any, ...],
        func_kwargs: dict[str, Any],
        *args: DP.args,
        **kwargs: DP.kwargs,
    ) -> Any: ...


@runtime_checkable
class DecoratorClass(Protocol[DP]):
    """
    装饰器类协议, 定义装饰器类的标准签名. 

    装饰器类应实现以下方法: 
    - __init__: 接收被装饰的函数和装饰器参数
    - __call__: 包装并调用被装饰的函数

    用途:
        用于类型检查, 确保装饰器类符合预期的签名格式. 
    """

    def __init__(
        self, func: Callable[..., Any], *args: DP.args, **kwargs: DP.kwargs
    ) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class Params(Generic[DP]):
    """
    参数容器类, 用于显式收集和传递装饰器参数. 

    特性:
        - 支持位置参数和关键字参数的统一传递
        - 可跨阶段传递, 避免上下文信息丢失
        - 与 Ellipsis 配合使用时支持参数跳过功能
    """

    @overload
    def __init__(self, *args: DP.args, **kwargs: DP.kwargs) -> None: ...
    @overload
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


class Decorator(Generic[DP]):
    """
    通用装饰器工厂类. 

    该类提供统一的装饰器工厂接口, 通过抽象装饰器的参数收集与目标绑定逻辑, 
    支持多种使用模式, 简化装饰器的编写过程. 

    主要功能:
        - 使用 `Params` 对象统一管理装饰器参数
        - 支持直接传参的简化语法(可能产生歧义)
        - 支持分阶段传参: 多次调用逐步累积参数
        - 在参数合并时自动处理关键字参数到位置参数的转换
        - 支持 Ellipsis (`...`) 占位符: 跳过参数, 保留之前的值
        - 同时兼容函数式和类式装饰器
        - 保留完整的函数签名, 确保 IDE 友好性

    属性:
        Decorator: 装饰器函数或类
        args: 已收集的位置参数
        kwargs: 已收集的关键字参数

    使用方式:
        1. 作为装饰器工厂使用:
           @Decorator
           def my_decorator(...): ...
        2. 创建装饰器实例:
           deco = Decorator(my_decorator)
           @deco(param="value")
           def func(): ...

    传参模式:
        1. **无参模式**: 返回当前实例
            @my_decorator
            def foo(): ...
        2. **有参模式**: 直接传参
            @my_decorator(prefix=">>>", suffix="<<<")
            def bar(): ...
        3. **分阶段传参**: 多次调用逐步累积参数
            deco = my_decorator(prefix=">>>")
            @deco(suffix="<<<")
            def baz(): ...
        4. **使用 Params 显式传参: 避免第一个参数歧义**
            params = Params(prefix=">>>", suffix="<<<")
            @my_decorator(params)
            def qux(): ...
        5. **Ellipsis 占位符**: 跳过参数, 保留之前的值
            @my_decorator(..., suffix="<<<")
            def quux(): ...
    """

    decorator: DecoratorFunction[DP] | type[DecoratorClass[DP]]
    signature: inspect.Signature
    args_name_index: dict[str, int]
    args: list[Any]
    kwargs: dict[str, Any]

    def __init__(
        self,
        target: DecoratorFunction[DP] | type[DecoratorClass[DP]] | Decorator[DP],
    ) -> None:
        """
        初始化装饰器工厂. 

        参数:
            target: 被简化的装饰器函数或装饰器类, 必须符合相应协议
        """
        if isinstance(target, Decorator):
            self.decorator = target.decorator
            self.signature = target.signature
            self.args_name_index = target.args_name_index
            self.args = target.args
            self.kwargs = target.kwargs
        else:
            self.decorator = target
            self.signature = inspect.signature(self.decorator)
            self.args_name_index = {}
            self.args = list()
            self.kwargs = dict()
            self._initialize_parameters()

    @overload
    def __call__(self, func: Callable[P, R], params: Params[DP]) -> Callable[P, R]: ...
    @overload
    def __call__(
        self, func: Callable[P, R], *args: DP.args, **kwargs: DP.kwargs
    ) -> Callable[P, R]: ...
    @overload
    def __call__(
        self, func: Callable[P, R], *args: Any, **kwargs: Any
    ) -> Callable[P, R]: ...
    @overload
    def __call__(self, params: Params[DP]) -> Decorator[DP]: ...
    @overload
    def __call__(self, *args: DP.args, **kwargs: DP.kwargs) -> Decorator[DP]: ...
    @overload
    def __call__(self, *args: Any, **kwargs: Any) -> Decorator[DP]: ...

    def __call__(self, *args: Any, **next_kwargs: Any) -> Any:
        """
        实现装饰器的参数收集和函数包装逻辑. 

        根据传入参数的不同类型, 自动识别并处理不同的使用模式. 
        具体使用模式请参考类的文档字符串. 
        """
        if not args and not next_kwargs:
            return self

        next_args = list(args)
        next_kwargs = dict(next_kwargs)
        func, next_args = self._get_func(next_args)
        next_args, next_kwargs = self._resolve_params(next_args, next_kwargs)
        next_args, next_kwargs = self._merge_params(next_args, next_kwargs)

        if func:
            next_args, next_kwargs = self._trim_params(next_args, next_kwargs)
            if inspect.isclass(self.decorator):
                self.signature.bind(func, *next_args, **next_kwargs)
                wrapper = self.decorator(func, *tuple(next_args), **next_kwargs)
            else:
                self.signature.bind(func, (), {}, *next_args, **next_kwargs)
                wrapper = self._create_function(func, next_args, next_kwargs)
            functools.update_wrapper(wrapper, func)
            return wrapper

        next_self = type(self)(self)
        next_self.args = next_args
        next_self.kwargs = next_kwargs
        return next_self

    def _get_func(self, args: list[Any]) -> tuple[Callable[..., Any] | None, list[Any]]:
        """
        从参数中提取函数对象和剩余参数. 
        """
        if args and callable(args[0]):
            return args[0], args[1:]
        return None, args

    def _resolve_params(
        self, args: list[Any], kwargs: dict[str, Any]
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        从参数中提取 `Params` 对象并返回其解包后的参数. 

        支持形式:
            - 位置参数传入 `Params` 实例
            - 关键字参数传入 `params=Params` 实例
        """
        if (len(args) + len(kwargs)) == 1:
            params = args[0] if args else kwargs.get("params")
            if isinstance(params, Params):
                return list(params.args), params.kwargs
        return args, kwargs

    def _merge_params(
        self, args: list[Any], kwargs: dict[str, Any]
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        合并参数, 将当前实例的参数与新传入的参数合并. 
        """
        merged_args = list(
            old if new is Ellipsis else new
            for new, old in zip_longest(args, self.args, fillvalue=Ellipsis)
        )

        merged_kwargs = dict(self.kwargs)
        for k, v in kwargs.items():
            if v is Ellipsis:
                continue

            index = self.args_name_index.get(k)
            if index is not None:
                # 列表乘负数时结果为空, 相当于 `[Ellipsis] * 0`
                merged_args += [Ellipsis] * (index - len(merged_args) + 1)
                merged_args[index] = v
            else:
                merged_kwargs[k] = v

        return merged_args, merged_kwargs

    def _trim_params(
        self, args: list[Any], kwargs: dict[str, Any]
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        从参数中移除占位符. 
        """
        args = [arg for arg in args if arg is not Ellipsis]
        kwargs = {k: v for k, v in kwargs.items() if v is not Ellipsis}
        return args, kwargs

    def _create_function(
        self,
        func: Callable[P, R],
        decorator_args: list[Any],
        decorator_kwargs: dict[str, Any],
    ) -> Callable[P, R]:
        """
        创建一个闭包装饰器, 将装饰器参数封装起来. 
        """
        decorator = cast(DecoratorFunction, self.decorator)

        def wrapper(*func_args: P.args, **func_kwargs: P.kwargs) -> R:
            return decorator(
                func, func_args, func_kwargs, *decorator_args, **decorator_kwargs
            )

        return wrapper

    def _initialize_parameters(self) -> None:
        """
        初始化参数容器, 根据装饰器类型和参数签名设置默认值. 
        """
        parameters = list(self.signature.parameters.values())
        if not inspect.isclass(self.decorator):
            parameters = parameters[3:]

        for index, parameter in enumerate(parameters):
            default = (
                Ellipsis
                if parameter.default == inspect.Parameter.empty
                else parameter.default
            )
            if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                self.args.append(default)
            if parameter.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                self.args_name_index[parameter.name] = index
                self.args.append(default)
            if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
                self.kwargs[parameter.name] = default
