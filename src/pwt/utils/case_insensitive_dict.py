"""
提供一个大小写不敏感的字典实现.

设计目标:
- 对字符串键使用大小写折叠(casefold)进行归一化, 确保跨语言一致的大小写不敏感.
- 非字符串键保持原样(支持所有可哈希类型作为键).
- 保留"最后一次写入"的原始键形式; 遍历时输出当前的原始大小写.
- 基于 collections.abc.MutableMapping, 只需实现核心方法, 其余辅助行为沿用默认实现.
- 覆盖写入同一逻辑键(例如 "PATH" 与 "Path")时, 以最后一次写入的原始键形式为准.

主要组件:
- CaseInsensitiveDict: 大小写不敏感键的字典类

示例:
    >>> from case_insensitive_dict import CaseInsensitiveDict
    >>> d = CaseInsensitiveDict({"PATH": "A"}, {"Path": "B"}, {"Home": "C"})
    >>> d["path"]
    'B'
    >>> "PaTh" in d
    True
    >>> list(d.keys())
    ['Path', 'Home']

    # 非字符串键保持原样
    >>> d = CaseInsensitiveDict()
    >>> d[123] = "num"
    >>> 123 in d
    True
    >>> d["123"]
    Traceback (most recent call last):
        ...
    KeyError: '123'
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any, Generic, Hashable, Iterator, Mapping, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class CaseInsensitiveDict(MutableMapping[K, V], Generic[K, V]):
    """
    对字符串键大小写不敏感的字典实现.

    内部结构:
    - self._data: {原始键: 值}
    - self._map:  {归一化键: 原始键}
      归一化规则: 对 str 使用 .casefold(); 非 str 键保持原样.

    查找与更新逻辑:
    - 存储: 若归一化后的逻辑键已存在, 先删除旧的原始键, 再写入新值与新原始键映射.
    - 取值: 通过归一化键在 _map 找到原始键, 再到 _data 取值.
    - 删除: 同步从 _map 与 _data 删除; 若键不存在, 抛 KeyError.
    - 遍历: 遍历 _data 的原始键, 保留用户最后一次写入的大小写.

    特性:
    - **大小写不敏感(仅字符串)**: `"PATH"`, `"Path"`, `"path"` 视为同一逻辑键.
    - **保留原始键形态**: 覆盖写入后, `keys()`/`items()` 展示最后一次写入的大小写.
    - **广泛键支持**: 非字符串键(如 int/tuple/frozenset)按原样处理.
    """

    def __init__(self, *args: Mapping[K, V] | Iterator[tuple[K, V]]) -> None:
        self._data: dict[K, V] = {}
        self._map: dict[Hashable, K] = {}
        for arg in args:
            self.update(arg)

    def __setitem__(self, key: K, value: V) -> None:
        norm_key = self._normalize_key(key)
        if norm_key in self._map:
            orig_key = self._map.pop(norm_key)
            self._data.pop(orig_key, None)
        self._data[key] = value
        self._map[norm_key] = key

    def __getitem__(self, key: K) -> V:
        norm_key = self._normalize_key(key)
        orig_key = self._map[norm_key]
        return self._data[orig_key]

    def __delitem__(self, key: K) -> None:
        norm_key = self._normalize_key(key)
        orig_key = self._map.pop(norm_key)
        del self._data[orig_key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: Any) -> bool:
        norm_key = self._normalize_key(key)
        return norm_key in self._map

    def __repr__(self) -> str:
        inner = ", ".join(f"{k!r}: {v!r}" for k, v in self._data.items())
        return f"{self.__class__.__name__}({{{inner}}})"

    def _normalize_key(self, key: K) -> Hashable:
        if isinstance(key, str):
            return key.casefold()
        return key
