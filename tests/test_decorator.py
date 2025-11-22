"""
装饰器模块的单元测试

测试 Decorator 类的核心功能, 包括: 
- 函数式和类式装饰器的基本使用
- 参数传递和分阶段传参
- Ellipsis 占位符功能
- 函数签名保留
- 边界情况和错误处理
- 关键字参数映射功能
"""

import time
import unittest
from typing import Any, Callable, Dict, Tuple

from pwt.utils.decorator import Decorator, Params


class TestDecorator(unittest.TestCase):
    """测试 Decorator 类的核心功能"""

    def setUp(self):
        """测试前的准备工作"""

        # 创建一个简单的函数式装饰器用于测试
        def simple_function_decorator(
            func: Callable[..., Any],
            func_args: Tuple[Any, ...],
            func_kwargs: Dict[str, Any],
            prefix: str = "",
            suffix: str = "",
            kw: str = "abc",
        ) -> Any:
            """简单的函数式装饰器, 用于测试"""
            result = func(*func_args, **func_kwargs)
            return f"{prefix}{result}{suffix}"

        self.simple_function_decorator = simple_function_decorator

        # 创建一个简单的类式装饰器用于测试
        class SimpleClassDecorator:
            """简单的类式装饰器, 用于测试"""

            def __init__(
                self, func: Callable[..., Any], prefix: str = "", suffix: str = ""
            ):
                self.func = func
                self.prefix = prefix
                self.suffix = suffix

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                result = self.func(*args, **kwargs)
                return f"{self.prefix}{result}{self.suffix}"

        self.SimpleClassDecorator = SimpleClassDecorator

        # 创建一个带状态的类式装饰器用于测试
        class StatefulClassDecorator:
            """带状态的类式装饰器, 用于测试"""

            def __init__(self, func: Callable[..., Any], counter: int = 0):
                self.func = func
                self.counter = counter

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                self.counter += 1
                result = self.func(*args, **kwargs)
                return f"Call #{self.counter}: {result}"

        self.StatefulClassDecorator = StatefulClassDecorator

        # 用于关键字参数映射测试的装饰器
        def test_decorator(
            func: Callable[..., Any],
            func_args: Tuple[Any, ...],
            func_kwargs: Dict[str, Any],
            param1: str = "default1",
            param2: str = "default2",
            param3: str = "default3",
        ) -> Any:
            """测试装饰器, 用于关键字参数映射测试"""
            return f"{param1}|{param2}|{param3}: {func(*func_args, **func_kwargs)}"

        self.test_decorator = test_decorator

    def test_basic_function_decorator(self):
        """测试函数式装饰器的基本使用"""
        decorator = Decorator(self.simple_function_decorator)

        # 无参使用
        @decorator
        def func():
            return "hello"

        self.assertEqual(func(), "hello")

        # 有参使用
        @decorator(prefix=">>>", suffix="<<<")
        def func2():
            return "hello"

        self.assertEqual(func2(), ">>>hello<<<")

    def test_basic_class_decorator(self):
        """测试类式装饰器的基本使用"""
        decorator = Decorator(self.SimpleClassDecorator)

        # 无参使用
        @decorator
        def func():
            return "hello"

        self.assertEqual(func(), "hello")

        # 有参使用
        @decorator(prefix=">>>", suffix="<<<")
        def func2():
            return "hello"

        self.assertEqual(func2(), ">>>hello<<<")

    def test_staged_arguments(self):
        """测试分阶段传参功能"""
        decorator = Decorator(self.simple_function_decorator)

        # 分阶段配置
        stage1 = decorator(prefix=">>>")
        stage2 = stage1(suffix="<<<")

        @stage2
        def func():
            return "hello"

        self.assertEqual(func(), ">>>hello<<<")

    def test_ellipsis_placeholder(self):
        """测试 Ellipsis 占位符功能"""
        decorator = Decorator(self.simple_function_decorator)

        # 使用 Ellipsis 跳过参数
        stage1 = decorator(">>>", "default")
        stage2 = stage1(..., "<<<")

        @stage2
        def func():
            return "hello"

        self.assertEqual(func(), ">>>hello<<<")

    def test_function_preservation(self):
        """测试函数签名和属性的保留"""
        decorator = Decorator(self.simple_function_decorator)

        def original_func(x: int, y: int = 0) -> str:
            """原始函数的文档字符串"""
            return f"result: {x + y}"

        original_func.custom_attr = "test_attr"

        decorated_func = decorator(prefix=">>>", suffix="<<<")(original_func)

        # 测试函数名保留
        self.assertEqual(decorated_func.__name__, "original_func")
        # 测试文档字符串保留
        self.assertEqual(decorated_func.__doc__, "原始函数的文档字符串")
        # 测试自定义属性保留
        self.assertEqual(decorated_func.custom_attr, "test_attr")

    def test_complex_usage_scenario(self):
        """测试复杂的使用场景"""

        def complex_decorator(
            func: Callable[..., Any],
            func_args: Tuple[Any, ...],
            func_kwargs: Dict[str, Any],
            multiplier: int = 1,
            formatter: str = "{}",
        ) -> Any:
            result = func(*func_args, **func_kwargs)
            return formatter.format(result * multiplier)

        decorator = Decorator(complex_decorator)

        # 分阶段配置装饰器
        stage1 = decorator(multiplier=2)
        stage2 = stage1(formatter="Result: {}")

        @stage2
        def calculate(x: int, y: int) -> int:
            return x + y

        result = calculate(3, 4)
        self.assertEqual(result, "Result: 14")  # (3+4)*2 = 14

    def test_stateful_decorator(self):
        """测试带状态的装饰器"""
        decorator = Decorator(self.StatefulClassDecorator)

        @decorator(counter=0)
        def func():
            return "hello"

        # 多次调用, 计数器应该递增
        result1 = func()
        result2 = func()
        result3 = func()

        self.assertEqual(result1, "Call #1: hello")
        self.assertEqual(result2, "Call #2: hello")
        self.assertEqual(result3, "Call #3: hello")

    def test_keyword_argument_mapping(self):
        """测试关键字参数映射功能"""
        decorator = Decorator(self.test_decorator)

        # 关键字参数映射到位置参数
        @decorator(param1="first", param2="second", param3="third")
        def func():
            return "hello"

        result = func()
        self.assertEqual(result, "first|second|third: hello")

    def test_mixed_arguments_usage(self):
        """测试混合使用位置参数和关键字参数"""
        decorator = Decorator(self.test_decorator)

        # 位置参数 + 关键字参数
        @decorator("first", param3="third")
        def func():
            return "hello"

        result = func()
        self.assertEqual(result, "first|default2|third: hello")

    def test_keyword_overrides_positional(self):
        """测试关键字参数覆盖位置参数"""
        decorator = Decorator(self.test_decorator)
        decorator = decorator("positional1", "positional2", "positional3")

        @decorator(param2="keyword2")
        def func():
            return "hello"

        result = func()
        self.assertEqual(result, "positional1|keyword2|positional3: hello")

    def test_params_class_usage(self):
        """测试 Params 类的使用"""
        decorator = Decorator(self.simple_function_decorator)

        # 使用 Params 对象传参
        params = Params(prefix=">>>", suffix="<<<")

        @decorator(params)
        def func():
            return "hello"

        result = func()
        self.assertEqual(result, ">>>hello<<<")

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的装饰器类型
        with self.assertRaises(TypeError):
            Decorator("not_a_callable")  # type: ignore

        # 测试缺少必需参数
        def decorator_with_required(
            func: Callable[..., Any],
            func_args: Tuple[Any, ...],
            func_kwargs: Dict[str, Any],
            required_param: str,
        ) -> Any:
            return func(*func_args, **func_kwargs)

        decorator = Decorator(decorator_with_required)

        # 应该抛出异常, 因为缺少必需参数
        with self.assertRaises(TypeError):

            @decorator
            def func():
                return "hello"

    def test_edge_cases(self):
        """测试边界情况"""
        decorator = Decorator(self.simple_function_decorator)

        # 空字符串参数
        @decorator(prefix="", suffix="")
        def func():
            return "hello"

        self.assertEqual(func(), "hello")

        # None 值参数处理
        def none_handling_decorator(
            func: Callable[..., Any],
            func_args: Tuple[Any, ...],
            func_kwargs: Dict[str, Any],
            default_value: Any = None,
        ) -> Any:
            result = func(*func_args, **func_kwargs)
            return result if result is not None else default_value

        decorator = Decorator(none_handling_decorator)

        @decorator(default_value="Default")
        def func_returns_none():
            return None

        result = func_returns_none()
        self.assertEqual(result, "Default")

    def test_method_decorators(self):
        """测试类方法的装饰器"""
        decorator = Decorator(self.simple_function_decorator)

        class TestClass:
            @decorator(prefix="[", suffix="]")
            def method(self, x: int) -> str:
                return f"method result: {x}"

        obj = TestClass()
        result = obj.method(42)
        self.assertEqual(result, "[method result: 42]")

    def test_multiple_decorators(self):
        """测试多个装饰器的组合使用"""
        decorator1 = Decorator(self.simple_function_decorator)
        decorator2 = Decorator(self.SimpleClassDecorator)

        @decorator1(prefix="[", suffix="]")
        @decorator2(prefix="(", suffix=")")
        def func():
            return "hello"

        result = func()
        self.assertEqual(result, "[(hello)]")

    def test_decorator_reuse(self):
        """测试装饰器的重用"""
        decorator = Decorator(self.simple_function_decorator)

        # 重用同一个装饰器实例
        configured_decorator = decorator(prefix=">>>", suffix="<<<")

        @configured_decorator
        def func1():
            return "hello1"

        @configured_decorator
        def func2():
            return "hello2"

        result1 = func1()
        result2 = func2()

        self.assertEqual(result1, ">>>hello1<<<")
        self.assertEqual(result2, ">>>hello2<<<")

    def test_basic_performance(self):
        """测试基本性能"""
        decorator = Decorator(self.simple_function_decorator)

        @decorator(prefix=">>>", suffix="<<<")
        def fast_func():
            return "test"

        # 测试多次调用的性能
        start_time = time.time()
        for _ in range(1000):
            fast_func()
        end_time = time.time()

        # 确保1000次调用在合理时间内完成
        self.assertLess(end_time - start_time, 1.0)


if __name__ == "__main__":
    unittest.main()
