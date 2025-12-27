"""
重试模块单元测试

该测试文件覆盖了 pwt.utils.retry 模块的所有主要功能, 包括: 
- RetryState 类
- 各种重试装饰器 (Retry, SimpleRetry, AdvancedRetry)
- 间隔函数 (exponential_backoff_interval, fixd_interval)
- 可重试函数构造器 (retries_retryable, exception_retryable, results_retryable 等)
- 辅助函数 (_exponential_backoff, _truncate_middle)
"""

import time

import pytest

from pwt.utils.retry import (
    AdvancedRetry,
    Retry,
    RetryState,
    SimpleRetry,
    _exponential_backoff,
    _truncate_middle,
    all_retryable,
    any_retryable,
    exception_retryable,
    exponential_backoff_interval,
    fixd_interval,
    fixd_retryable,
    results_retryable,
    retries_retryable,
)


class TestRetryState:
    """测试 RetryState 类"""

    def test_retry_state_initialization(self):
        """测试 RetryState 初始化"""

        def test_func(a, b, c=3):
            return a + b + c

        state = RetryState(test_func, 1, 2, c=4)

        assert state.func == test_func
        assert state.args == (1, 2)
        assert state.kwargs == {"c": 4}
        assert state.attempts == 0
        assert state.delay == 0
        assert state.result is None
        assert state.exception is None

    def test_retry_state_str_representation(self):
        """测试 RetryState 的字符串表示"""

        def test_func():
            return "test"

        state = RetryState(test_func)
        state.attempts = 2
        state.delay = 1.5
        state.result = "success"

        str_repr = str(state)
        assert "attempts: 2" in str_repr
        assert "delay: 1.5" in str_repr
        assert "result: success" in str_repr
        assert "func: test_func" in str_repr


class TestIntervalFunctions:
    """测试间隔函数"""

    def test_fixd_interval(self):
        """测试固定间隔函数"""
        interval_func = fixd_interval(2.5)
        state = RetryState(lambda: None)

        assert interval_func(state) == 2.5

    def test_exponential_backoff_interval(self):
        """测试指数退避间隔函数"""
        interval_func = exponential_backoff_interval(factor=1, base=2, maximum=10)
        state = RetryState(lambda: None)

        # 测试不同重试次数的间隔
        state.attempts = 0
        assert interval_func(state) == 1  # 2^0 * 1 = 1

        state.attempts = 2
        assert interval_func(state) == 4  # 2^2 * 1 = 4

        state.attempts = 5
        assert interval_func(state) == 10  # 2^5 * 1 = 32, 但被最大值10限制

    def test_exponential_backoff_interval_with_jitter(self):
        """测试带抖动的指数退避间隔函数"""
        interval_func = exponential_backoff_interval(
            factor=1, base=2, maximum=10, jitter=True
        )
        state = RetryState(lambda: None)
        state.attempts = 3

        # 抖动应该在 [3, 8] 范围内
        delay = interval_func(state)
        assert 3 <= delay <= 8


class TestRetryableFunctions:
    """测试可重试函数构造器"""

    def test_retries_retryable(self):
        """测试重试次数判断函数"""
        retryable_func = retries_retryable(3)
        state = RetryState(lambda: None)

        state.attempts = 0
        assert retryable_func(state) is True

        state.attempts = 2
        assert retryable_func(state) is True

        state.attempts = 3
        assert retryable_func(state) is False

    def test_exception_retryable(self):
        """测试异常类型判断函数"""
        retryable_func = exception_retryable(ValueError, TypeError)
        state = RetryState(lambda: None)

        # 没有异常时返回 False
        state.exception = None
        assert retryable_func(state) is False

        # 匹配的异常返回 True
        state.exception = ValueError("test")
        assert retryable_func(state) is True

        state.exception = TypeError("test")
        assert retryable_func(state) is True

        # 不匹配的异常返回 False
        state.exception = RuntimeError("test")
        assert retryable_func(state) is False

    def test_results_retryable(self):
        """测试返回值判断函数"""
        retryable_func = results_retryable(None, "", [])
        state = RetryState(lambda: None)

        # 匹配的返回值返回 True
        state.result = None
        assert retryable_func(state) is True

        state.result = ""
        assert retryable_func(state) is True

        state.result = []
        assert retryable_func(state) is True

        # 不匹配的返回值返回 False
        state.result = "success"
        assert retryable_func(state) is False

    def test_fixd_retryable(self):
        """测试固定条件判断函数"""
        retryable_func = fixd_retryable(
            retries=3, exceptions=(ValueError,), results=(None,)
        )
        state = RetryState(lambda: None)

        # 测试重试次数限制
        state.attempts = 3
        state.exception = ValueError("test")
        assert retryable_func(state) is False  # 超过重试次数

        state.attempts = 2
        assert retryable_func(state) is True  # 在重试次数内, 有匹配异常

        # 测试返回值匹配
        state.exception = None
        state.result = None
        assert retryable_func(state) is True  # 匹配返回值

        state.result = "success"
        assert retryable_func(state) is False  # 不匹配返回值, 也没有异常

    def test_all_retryable(self):
        """测试全部条件判断函数"""
        condition1 = retries_retryable(3)
        condition2 = exception_retryable(ValueError)
        retryable_func = all_retryable(condition1, condition2)
        state = RetryState(lambda: None)

        state.attempts = 2
        state.exception = ValueError("test")
        assert retryable_func(state) is True  # 两个条件都满足

        state.attempts = 4
        assert retryable_func(state) is False  # 重试次数超过限制

    def test_any_retryable(self):
        """测试任意条件判断函数"""
        condition1 = retries_retryable(3)
        condition2 = exception_retryable(ValueError)
        retryable_func = any_retryable(condition1, condition2)
        state = RetryState(lambda: None)

        state.attempts = 2
        state.exception = None
        assert retryable_func(state) is True  # 重试次数条件满足

        state.attempts = 4
        state.exception = ValueError("test")
        assert retryable_func(state) is True  # 异常条件满足

        state.exception = None
        assert retryable_func(state) is False  # 两个条件都不满足


class TestSimpleRetry:
    """测试 SimpleRetry 装饰器"""

    def test_simple_retry_success_on_first_try(self):
        """测试第一次调用就成功的情况"""
        call_count = 0

        @SimpleRetry(delay=0.01, retries=3, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 1

    def test_simple_retry_success_after_retries(self):
        """测试重试后成功的情况"""
        call_count = 0

        @SimpleRetry(delay=0.01, retries=3, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 3

    def test_simple_retry_failure_after_max_retries(self):
        """测试达到最大重试次数后失败的情况"""
        call_count = 0

        @SimpleRetry(delay=0.01, retries=3, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fail")

        with pytest.raises(ValueError, match="always fail"):
            test_func()

        assert call_count == 4  # 初始调用 + 3次重试

    def test_simple_retry_with_unhandled_exception(self):
        """测试未处理的异常类型"""
        call_count = 0

        @SimpleRetry(delay=0.01, retries=3, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("unhandled exception")

        with pytest.raises(TypeError, match="unhandled exception"):
            test_func()

        assert call_count == 1  # 未处理的异常不会重试


class TestAdvancedRetry:
    """测试 AdvancedRetry 装饰器"""

    def test_advanced_retry_exponential_backoff(self):
        """测试指数退避功能"""
        call_count = 0
        start_time = time.time()

        @AdvancedRetry(factor=0.1, maximum=1, retries=2, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = test_func()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count == 3
        # 应该至少有两次延迟
        assert elapsed_time >= 0.02

    def test_advanced_retry_with_jitter(self):
        """测试带抖动的重试"""
        call_count = 0

        @AdvancedRetry(
            factor=0.1, maximum=1, jitter=True, retries=2, exceptions=(ValueError,)
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 3


class TestAsyncRetry:
    """测试异步重试功能"""

    @pytest.mark.asyncio
    async def test_async_simple_retry(self):
        """测试异步 SimpleRetry"""
        call_count = 0

        @SimpleRetry(delay=0.01, retries=3, exceptions=(ValueError,))
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "async-success"

        result = await async_func()

        assert result == "async-success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_advanced_retry(self):
        """测试异步 AdvancedRetry"""
        call_count = 0

        @AdvancedRetry(factor=0.1, maximum=1, retries=3, exceptions=(ValueError,))
        async def async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("fail")
            return "async-success"

        result = await async_func()

        assert result == "async-success"
        assert call_count == 2


class TestRetryDecorator:
    """测试基础的 Retry 装饰器"""

    def test_custom_retry_with_interval_and_retryable(self):
        """测试自定义间隔和重试条件"""
        call_count = 0

        def custom_interval(state):
            return 0.01 * (state.attempts + 1)  # 线性增长的间隔

        def custom_retryable(state):
            return state.attempts < 2 and isinstance(state.exception, ValueError)

        @Retry(interval=custom_interval, retryable=custom_retryable)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 3


class TestHelperFunctions:
    """测试辅助函数"""

    def test_exponential_backoff(self):
        """测试指数退避计算函数"""
        # 测试基本指数退避
        assert _exponential_backoff(1, 0, 10) == 1  # 2^0 * 1 = 1
        assert _exponential_backoff(1, 2, 10) == 4  # 2^2 * 1 = 4
        assert _exponential_backoff(2, 3, 20) == 16  # 2^3 * 2 = 16

        # 测试最大值限制
        assert _exponential_backoff(1, 5, 10) == 10  # 2^5 * 1 = 32, 但被最大值10限制

        # 测试非2的基数
        assert _exponential_backoff(1, 2, 10, base=3) == 9  # 3^2 * 1 = 9

    def test_truncate_middle(self):
        """测试字符串中间截断函数"""
        # 测试短字符串不截断
        assert _truncate_middle("abc", 10) == "abc"

        # 测试长字符串截断
        result = _truncate_middle("abcdefghijklmnopqrst", 10)
        assert " ... " in result
        assert len(result) == 10

        # 测试边界情况
        assert _truncate_middle("", 5) == " ... "
        assert _truncate_middle("abc", 3) == " ... "

        # 测试非字符串对象
        assert _truncate_middle([1, 2, 3], 10) == "[1, 2, 3]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
