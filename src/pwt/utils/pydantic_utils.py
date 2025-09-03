"""
基于 Pydantic v2 验证机制的通用工具集.

提供:
- 格式化 ValidationError 为结构化列表
- 构建通用字段转换器(单值 / 列表 / 字典)
- 构建通用字段检查器(单值 / 列表 / 字典)
- 扩展 BaseModel, 支持空值回退到字段默认值

转换器和检查器均以 BeforeValidator / AfterValidator 装饰器形式封装, 可直接应用于字段验证.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
)
from pydantic_core import PydanticCustomError, PydanticUndefined

from pwt.utils.expression import Expression


def format_validation_error(exc: ValidationError) -> list[dict[str, Any]]:
    """
    将 Pydantic 的 ValidationError 转换为结构化错误列表.

    Args:
        exc: Pydantic 抛出的验证异常对象.

    Returns:
        每个错误包含字段路径/提示信息/错误类型和原始输入值.
    """
    return [
        {
            "field": ".".join(map(str, error.get("loc", ()))),
            "message": error.get("msg", None),
            "type": error.get("type", None),
            "input": error.get("input", None),
        }
        for error in exc.errors()
    ]


def _noop(data: Any) -> Any:
    return data


def convert(
    func: Callable[..., Any] | None = None,
    expression: str | None = None,
    data_shape: Literal["obj", "list", "dict"] = "obj",
    ignore_none: bool = True,
    description: str | None = None,
    expr_context: dict[str, Any] | None = None,
    **func_kwds: Any,
) -> BeforeValidator:
    """
    构造一个在 Pydantic 验证前执行的值转换器.

    按顺序执行:
    1. 表达式处理(`expression` 不为空时)
    2. 自定义函数处理(`func` 不为空时)

    Args:
        func: 转换函数.
            - obj: 接收单值, 返回单值
            - list: 接收元素, 返回元素
            - dict: 接收 (key, value), 返回 (key, value)
        expression: 可选表达式字符串, dict 模式仅作用于 value.
        data_shape: 输入数据结构类型.
        ignore_none: 值为 None 时是否跳过转换.
        description: 自定义错误信息.

        expr_context: 表达式上下文字典, 仅作用于 `expression`.
        **func_kwds: 传给 `func` 的额外关键字参数.

    Returns:
        可用于 Pydantic 字段的转换器.
    """
    partial_func = partial(func, **func_kwds) if func else _noop
    partial_expr = (
        partial(Expression(expression).evaluate, **(expr_context or {}))
        if expression
        else _noop
    )

    def validator(data: Any) -> Any:
        if ignore_none and data is None:
            return data

        try:
            if data_shape == "list":
                result = []
                for value in data:
                    value = partial_expr(data=value)
                    value = partial_func(value)
                    result.append(value)
                return result
            elif data_shape == "dict":
                result = {}
                for key, value in data.items():
                    value = partial_expr(data=value)
                    key, value = partial_func((key, value))
                    result[key] = value
                return result
            else:
                value = partial_expr(data=data)
                value = partial_func(value)
                return value

        except Exception as ex:
            raise PydanticCustomError(
                "Convert failed",
                "{reason}",
                {"reason": description or str(ex)},
            )

    return BeforeValidator(validator)


def check(
    func: Callable[..., Any] | None = None,
    expression: str | None = None,
    data_shape: Literal["obj", "list", "dict"] = "obj",
    ignore_none: bool = True,
    check_result: bool = False,
    description: str | None = None,
    expr_context: dict[str, Any] | None = None,
    **func_kwds: Any,
) -> AfterValidator:
    """
    构造一个在 Pydantic 验证后执行的检查器.

    按顺序执行:
    1. 表达式处理(`expression` 不为空时)
    2. 检查函数(`func` 不为空时)

    Args:
        func: 检查函数.
            - obj: 接收单值
            - list: 接收列表元素
            - dict: 接收 (key, value) 元组
        expression: 可选表达式字符串, dict 模式仅作用于 value.
        data_shape: 输入数据结构类型.
        ignore_none: 值为 None 时是否跳过检查.
        check_result: 是否检查函数返回值为真.
        description: 自定义错误信息.

        expr_context: 表达式上下文字典, 仅作用于 `expression`.
        **func_kwds: 传给 `func` 的额外关键字参数.

    Returns:
        可用于 Pydantic 字段的检查器.
    """
    partial_func = partial(func, **func_kwds) if func else _noop
    partial_expr = (
        partial(Expression(expression).evaluate, **(expr_context or {}))
        if expression
        else _noop
    )

    def validator(data: Any) -> Any:
        if ignore_none and data is None:
            return data

        try:
            if data_shape == "list":
                it = (partial_expr(data=value) for value in data)
            elif data_shape == "dict":
                it = ((key, partial_expr(data=value)) for key, value in data.items())
            else:
                it = (partial_expr(data=value) for value in [data])

            for value in it:
                result = partial_func(value)
                if check_result and not result:
                    raise ValueError("Return value check failed")
        except Exception as ex:
            raise PydanticCustomError(
                "Check failed",
                "{reason}",
                {"reason": description or str(ex)},
            )
        return data

    return AfterValidator(validator)


class BaseModelEx(BaseModel):
    """
    扩展版 BaseModel.

    特性:
    - 当字段值为空(空序列/空集合/空字符串/None)时, 自动回退到字段默认值(若有)
    - 可通过配置项 `validate_default` 控制默认值是否经过验证
    """

    @field_validator("*", mode="wrap")
    @classmethod
    def use_default_value(
        cls: type[BaseModelEx],
        value: Any,
        validator: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
        /,
    ) -> Any:
        if value in ([], {}, (), set(), "", None):
            if info and info.field_name:
                field_info = cls.model_fields.get(info.field_name)
                if field_info:
                    default = field_info.get_default(call_default_factory=True)
                    if default is not PydanticUndefined:
                        if info.config and info.config.get("validate_default"):
                            return validator(default)
                        return default
        return validator(value)
