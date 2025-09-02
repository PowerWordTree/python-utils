"""
json_normalizer
===============

提供一个通用的 Python 对象归一化工具, 将任意对象转换为
JSON 友好的结构(dict / list / 基础类型), 用于日志记录/
调试或序列化前的预处理.

主要特性:
- 支持基础类型/二进制类型/时间类型/异常对象/映射/可迭代对象等.
- 可选最大递归深度限制(max_depth).
- 可选循环引用检测(check_circular), 输出 JSONPath 风格的 $ref.
- 保留类型信息($type)/深度截断标记($depth)/可调用对象标记($callable).
- 基于 functools.singledispatch, 可扩展自定义类型的归一化逻辑.

典型用途:
- 结构化日志(JSON 格式)
- 调试输出复杂对象
- 序列化前的预处理
"""

import time
import traceback
import types
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from functools import singledispatch
from typing import Any, Literal, NamedTuple


class NormalizeContext(NamedTuple):
    """
    归一化过程的上下文信息.

    Attributes:
        max_depth (int): 最大递归深度(0 表示不限制).
        check_circular (bool): 是否检测循环引用.
        path (list[str | int]): 当前递归路径(键或索引).
        memo (dict[int, int]): 已访问对象的 id 到路径深度的映射, 用于循环检测.
    """

    max_depth: int
    check_circular: bool
    path: list[str | int]
    memo: dict[int, int]


def normalize(value: Any, *, max_depth: int = 0, check_circular: bool = False) -> Any:
    """
    将任意 Python 对象归一化为 JSON 友好的结构.

    Args:
        value: 任意 Python 对象.
        max_depth: 最大递归深度(0 表示不限制).
        check_circular: 是否检测循环引用.

    Returns:
        归一化后的对象(基础类型/dict/list).
    """
    context = NormalizeContext(max_depth, check_circular, [], {id(value): 0})
    return _dispatch(value, context)


def _normalize_key(key: Any) -> str:
    """将映射的键转换为 JSON 友好的字符串, 同时保留类型信息."""
    # 常见 JSON 原生类型
    if isinstance(key, bool):
        return "true" if key else "false"
    if key is None:
        return "null"
    if isinstance(key, (str, int, float)):
        return str(key)

    # 其他对象类型
    type_name = type(key).__name__
    try:
        key_str = str(key)
    except Exception:
        key_str = f"<unprintable {type_name}>"

    # 组合成可读且带类型的键
    return f"<{type_name}:{key_str}>"


def _render_path(
    path: list[str | int],
    style: Literal["jsonpath", "slash", "dotlist"] = "jsonpath",
) -> str:
    """
    将路径列表渲染为字符串表示.

    Args:
        path: 路径元素列表(键或索引).
        style: 路径格式:
            - "jsonpath": $.a[0].b
            - "slash": /a/0/b
            - "dotlist": a.0.b

    Returns:
        格式化后的路径字符串.
    """
    if style == "jsonpath":
        parts = (f"[{p}]" if isinstance(p, int) else f".{p}" for p in path)
        return "$" + "".join(parts)
    elif style == "slash":
        return "/" + "/".join(str(p) for p in path)
    elif style == "dotlist":
        return ".".join(str(p) for p in path)
    else:
        raise ValueError(f"Unknown style: {style}")


def _recurse(value: Any, key: str | int, context: NormalizeContext) -> Any:
    """
    递归归一化子节点.

    Args:
        value: 当前值.
        key: 当前值在父容器中的键或索引.
        context: 归一化上下文.

    Returns:
        归一化后的值.
    """
    # 深度限制检查
    if context.max_depth > 0 and len(context.path) >= context.max_depth:
        return {"$depth": "<Max depth reached>"}

    # 基本类型直接返回
    if isinstance(value, (str, int, float, bool, type(None))):
        return value

    # 循环引用检测
    value_id = id(value)
    if context.check_circular and value_id in context.memo:
        path = _render_path(context.path[: context.memo[value_id]])
        return {"$ref": path}

    # 进入递归
    context.path.append(key)
    context.memo[value_id] = len(context.path)
    value = _dispatch(value, context)
    context.memo.pop(value_id, None)
    context.path.pop()
    return value


@singledispatch
def _dispatch(value: Any, context: NormalizeContext) -> Any:
    """
    类型分发入口. 根据对象类型调用对应的归一化处理函数.

    默认处理:
        - 收集 __slots__ 和 __dict__ 中的非私有属性.
        - 如果有属性则输出 $type + 属性字典.
        - 否则输出 $type + $value(str(value)).

    Args:
        value: 待处理对象.
        context: 归一化上下文.

    Returns:
        归一化后的值.
    """
    keys = set()
    if hasattr(value, "__slots__"):
        keys.update(k for k in value.__slots__)
    if hasattr(value, "__dict__"):
        keys.update(k for k in value.__dict__.keys())

    result = {}
    for k in keys:
        if k.startswith("_"):
            continue
        v = getattr(value, k, None)
        result[k] = _recurse(v, k, context)

    if result:
        return {"$type": type(value).__name__, **result}
    return {"$type": type(value).__name__, "$value": str(value)}


@_dispatch.register(str)
@_dispatch.register(int)
@_dispatch.register(float)
@_dispatch.register(bool)
@_dispatch.register(type(None))
def _(value: str, context: NormalizeContext) -> Any:
    """基础类型直接返回原值."""
    return value


@_dispatch.register(bytes)
@_dispatch.register(bytearray)
@_dispatch.register(memoryview)
def _(value: bytes | bytearray | memoryview, context: NormalizeContext) -> Any:
    """二进制类型转为十六进制字符串, 并保留原始类型名."""
    return {"$type": type(value).__name__, "$hex": value.hex()}


@_dispatch.register(datetime)
def _(value: datetime, context: NormalizeContext) -> Any:
    """datetime 转为 ISO 格式字符串(微秒精度)."""
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")


@_dispatch.register(time.struct_time)
def _(value: time.struct_time, context: NormalizeContext) -> Any:
    """time.struct_time 转为 ISO 格式字符串(秒精度)."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", value)


@_dispatch.register(BaseException)
def _(value: BaseException, context: NormalizeContext) -> Any:
    """异常对象转为包含类型/消息和 traceback 的字典."""
    typ = type(value)
    tb = value.__traceback__
    return {
        "$type": f"{typ.__module__}.{typ.__name__}",
        "message": str(value),
        "traceback": traceback.format_exception(typ, value, tb),
    }


@_dispatch.register(Mapping)
def _(value: Mapping, context: NormalizeContext) -> Any:
    """映射类型: 键值递归归一化."""
    result = {}
    for k, v in value.items():
        k = _normalize_key(k)
        result[k] = _recurse(v, k, context)
    return result


@_dispatch.register(Iterable)
def _(value: Iterable, context: NormalizeContext) -> Any:
    """可迭代类型(非字符串): 递归归一化为列表."""
    result = []
    for i, v in enumerate(value):
        result.append(_recurse(v, i, context))
    return result


@_dispatch.register(types.FunctionType)
@_dispatch.register(types.MethodType)
@_dispatch.register(types.BuiltinFunctionType)
@_dispatch.register(types.BuiltinMethodType)
def _(value: Callable, context: NormalizeContext) -> Any:
    """可调用对象转为 {"$callable": "<callable name>"}."""
    name = getattr(value, "__name__", value.__class__.__name__)
    return {"$callable": f"<callable {name}>"}
