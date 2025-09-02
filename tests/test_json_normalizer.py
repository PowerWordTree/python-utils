# tests/test_normalize.py
import time
from datetime import datetime

import pytest

from pwt.utils.json_normalizer import normalize  # 调整为你的模块名


def test_primitives_pass_through():
    assert normalize("hello") == "hello"
    assert normalize(123) == 123
    assert normalize(1.5) == 1.5
    assert normalize(True) is True
    assert normalize(None) is None


@pytest.mark.parametrize(
    "blob", [b"\x00\xffAZ", bytearray(b"\x00\xffAZ"), memoryview(b"\x00\xffAZ")]
)
def test_bytes_like_hex_and_type(blob):
    out = normalize(blob)
    assert isinstance(out, dict)
    assert out["$type"] == type(blob).__name__
    assert out["$hex"] == b"\x00\xffAZ".hex()


def test_memoryview_slice_and_stride():
    mv = memoryview(b"abcdef")[1:5:2]  # b, d -> 0x62 0x64
    out = normalize(mv)
    assert out["$type"] == "memoryview"
    assert out["$hex"] == b"bd".hex()


def test_datetime_format():
    dt = datetime(2023, 1, 2, 3, 4, 5, 678901)
    assert normalize(dt) == "2023-01-02T03:04:05.678901"


def test_struct_time_format():
    st = time.gmtime(0)  # 1970-01-01T00:00:00 UTC
    assert normalize(st) == "1970-01-01T00:00:00"


def test_exception_serialization_includes_type_message_traceback():
    try:
        raise ValueError("boom")
    except ValueError as e:
        out = normalize(e)
    assert out["$type"] == "builtins.ValueError"
    assert out["message"] == "boom"
    tb = "\n".join(out["traceback"])
    assert isinstance(tb, str) and len(tb) > 0
    assert "ValueError" in tb and "boom" in tb
    assert "Traceback (most recent call last)" in tb


def test_mapping_key_normalization_and_recursion():
    data = {True: 1, False: 0, None: 2, 2: {"k": 3}}
    out = normalize(data)
    # 键应为字符串
    assert set(out.keys()) == {"true", "false", "null", "2"}
    assert out["true"] == 1 and out["false"] == 0 and out["null"] == 2
    assert out["2"] == {"k": 3}


def test_mapping_self_reference_ref_path_root():
    d = {}
    d["self"] = d
    out = normalize(d, check_circular=True)
    assert out["self"] == {"$ref": "$"}


def test_iterable_list_tuple_generator():
    gen = (i for i in [1, 2, 3])
    assert normalize([1, 2, 3]) == [1, 2, 3]
    assert normalize((1, 2, 3)) == [1, 2, 3]  # 统一成 list
    assert normalize(gen) == [1, 2, 3]


def test_iterable_nested_and_recursion():
    obj = [{"x": 1}, (2, 3)]
    out = normalize(obj)
    assert out == [{"x": 1}, [2, 3]]


def test_object_with_public_and_private_attrs_filtered_and_typed():
    class P:
        __slots__ = ("a", "_b")

        def __init__(self):
            self.a = 1
            self._b = 2

    out = normalize(P())
    assert out["$type"] == "P"
    assert out["a"] == 1
    assert "_b" not in out


def test_object_without_public_attrs_falls_back_to_value():
    class Q:
        def __str__(self):
            return "Q!"

    out = normalize(Q())
    assert out == {"$type": "Q", "$value": "Q!"}


def test_max_depth_limits_recursion_in_nested_structures():
    obj = {"a": [{"b": 1}]}
    out1 = normalize(obj, max_depth=1)
    # 深度=1: 第一层还能进入到 "a", 但其子元素会被截断
    assert out1 == {"a": [{"$depth": "<Max depth reached>"}]}

    out2 = normalize(obj, max_depth=2)
    print(out2)
    # 深度=2: 进入 list 的第一个元素, 继续递归一层生成 {"b":1}
    assert out2 == {"a": [{"b": {"$depth": "<Max depth reached>"}}]}


def test_list_self_reference_ref_path_root():
    lst = []
    lst.append(lst)
    out = normalize(lst, check_circular=True)
    assert out == [{"$ref": "$"}]


def test_callable_function_builtin_and_method():
    def foo(x):  # noqa
        return x

    out_fn = normalize(foo)
    assert out_fn == {"$callable": "<callable foo>"}

    out_builtin = normalize(len)
    assert out_builtin == {"$callable": "<callable len>"}

    class C:
        def m(self):  # noqa
            return 1

    c = C()
    out_method = normalize(c.m)
    assert out_method == {"$callable": "<callable m>"}

    # 也覆盖内建类型方法(BuiltinMethodType), 如 list.append
    out_builtin_method = normalize([].append)
    assert out_builtin_method == {"$callable": "<callable append>"}


def test_string_not_treated_as_iterable_due_to_dispatch():
    # 若字符串被 Iterable 分支处理, 将会被拆成字符列表, 这里应保持原样
    assert normalize("abc") == "abc"


def test_bool_not_treated_as_int_by_dispatch():
    # 若未单独注册 bool, 可能走 int 分支; 当前实现已单独注册, 应保持布尔语义
    assert normalize(True) is True
    assert normalize(False) is False
