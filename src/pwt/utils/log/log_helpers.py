from __future__ import annotations

import json
import logging
import string
import sys
import traceback
from types import MappingProxyType
from typing import Any, Iterable, Literal

from pwt.utils import json_normalizer


def get_logger_adapter(name: str | None = None) -> LoggerAdapter:
    return LoggerAdapter(logging.getLogger(name))


def get_standard_logger_adapter(name: str | None = None) -> LoggerAdapter:
    """
    获取日志记录器并进行基本配置.

    参数:
        name (str | None): 日志记录器的名称.

    返回:
        logging.Logger: 配置好的日志记录器.
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = StandardHandler()
    formatter = EnhancedFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return LoggerAdapter(logger)


class StandardHandler(logging.Handler):
    """
    标准日志处理器, 用于将日志输出到标准输出流或标准错误流.
    """

    def __init__(self):
        super().__init__()
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def flush(self):
        with self.lock:  # type: ignore
            self.stdout.flush()
            self.stderr.flush()

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stdout if record.levelno < logging.WARNING else self.stderr
            stream.write(msg + "\n")
            stream.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    def __repr__(self):
        level = logging.getLevelName(self.level)
        name = "<stdout> <stderr>"
        cls = type(self).__name__
        return f"<{cls} {name} ({level})>"


class EnhancedFormatter(logging.Formatter):
    """
    扩展的日志格式化器
    """

    # fmt: off
    RESERVED_FIELDS = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module',
        'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs',
        'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'taskName',
        'message', 'asctime', 'stacklevel', 'logger'
    }
    # fmt: on

    def __init__(
        self,
        textfmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "{",
        validate: bool = True,
        *,
        output_format: Literal["text", "json"] = "text",
        json_max_depth: int = 5,
    ) -> None:
        super().__init__(textfmt, datefmt, style, validate)
        self.output_format = output_format
        self.json_max_depth = json_max_depth

    def format(self, record: logging.LogRecord) -> str:
        record.message = self.getMessage(record)
        record.asctime = self.formatTime(record, self.datefmt)

        # 输出text日志
        if self.output_format == "text":
            return self.formatMessage(record)
        # 输出json日志
        return self.formatJson(record)

    def getMessage(self, record: logging.LogRecord) -> str:
        msg = str(record.msg)
        args = record.args or ()
        kwargs = vars(record)
        style = getattr(record, "_style", "%")

        try:
            if style == "%":
                return record.getMessage()
            elif style == "{":
                return msg.format(*args, **kwargs)
            elif style == "$":
                return string.Template(msg).safe_substitute(kwargs)
            return msg
        except Exception:
            return msg

    def formatJson(self, record: logging.LogRecord) -> str:
        json_dict = {
            # 基础字段
            "timestamp": record.asctime,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            # 系统信息
            "process": {"id": record.process, "name": record.processName},
            "thread": {"id": record.thread, "name": record.threadName},
            # 代码位置
            "location": {
                "module": record.module,
                "function": record.funcName,
                "file": record.pathname,
                "line": record.lineno,
            },
        }
        # 调试信息
        if record.exc_info:
            typ, value, tb = record.exc_info
            json_dict["exception"] = {
                "$type": f"{typ.__module__}.{typ.__name__}" if typ else None,
                "message": str(value) if value else None,
                "traceback": traceback.format_exception(typ, value, tb),
            }
        if record.stack_info:
            json_dict["stack"] = record.stack_info.splitlines()
        # 扩展字段
        for key, value in vars(record).items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                json_dict[key] = value

        return json.dumps(
            json_normalizer.normalize(json_dict, max_depth=self.json_max_depth),
            ensure_ascii=False,
            indent=2,  # separators=(",", ":"),  # DEBUG
            default=str,
        )


class LoggerAdapter:
    """
    日志适配器, 封装标准库 `logging.Logger`

    提供三种日志格式化风格:
    - `log`: `%` 占位符格式(默认 logging 行为)
    - `logf`: `{}` 格式化(`str.format` 风格)
    - `logt`: `$` 模板格式化(`string.Template` 风格)

    每种风格均提供完整的日志级别方法(`debug`/`info`/`warning`/`error`/`critical`)

    通过构造函数传入的 `extra` 字段会自动合并到每条日志记录的 `extra` 中.
    对于 `{}` 和 `$` 风格, 会调整 `extra` 结构以便格式化器直接使用,
    并在 `extra` 中注入 `_style` 字段.
    """

    def __init__(self, logger: logging.Logger, **extra: Any) -> None:
        self.logger = logger
        self.extra = extra

    def process(
        self,
        level: int,
        msg: str,
        style: Literal["%", "{", "$"],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[int, str, tuple[Any, ...], dict[str, Any]]:
        """
        预处理日志调用参数, 统一合并并调整 `extra` 字段.

        - 对于 `%` 风格:
            直接在现有 `extra` 基础上合并适配器实例的 `extra`.
        - 对于 `{` 和 `$` 风格:
            将原本的 `kwargs` 作为新的 `extra` 值嵌入, 并把原 `extra` 的键提升到顶层.

        无论哪种风格, 都会在最终的 `extra` 中注入 `_style` 字段, 用于指示格式化方式.
        """
        if style != "%":
            extra = kwargs.pop("extra", {})
            kwargs = {**extra, "extra": kwargs}
        kwargs["extra"] = {**self.extra, **kwargs.get("extra", {}), "_style": style}
        return level, msg, args, kwargs

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.CRITICAL, msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        level, msg, args, kwargs = self.process(level, msg, "%", args, kwargs)
        self.logger.log(level, msg, *args, **kwargs)

    def debugf(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logf(logging.DEBUG, msg, *args, **kwargs)

    def infof(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logf(logging.INFO, msg, *args, **kwargs)

    def warningf(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logf(logging.WARNING, msg, *args, **kwargs)

    def errorf(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logf(logging.ERROR, msg, *args, **kwargs)

    def criticalf(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logf(logging.CRITICAL, msg, *args, **kwargs)

    def logf(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        level, msg, args, kwargs = self.process(level, msg, "{", args, kwargs)
        self.logger.log(level, msg, *args, **kwargs)

    def debugt(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logt(logging.DEBUG, msg, *args, **kwargs)

    def infot(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logt(logging.INFO, msg, *args, **kwargs)

    def warningt(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logt(logging.WARNING, msg, *args, **kwargs)

    def errort(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logt(logging.ERROR, msg, *args, **kwargs)

    def criticalt(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logt(logging.CRITICAL, msg, *args, **kwargs)

    def logt(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        level, msg, args, kwargs = self.process(level, msg, "$", args, kwargs)
        self.logger.log(level, msg, *args, **kwargs)


def get_level_names_mapping():
    """
    兼容 Python 3.10 及以下版本的 logging.getLevelNamesMapping()
    返回: 名称 -> 数值 的映射(不可修改)
    """
    if hasattr(logging, "getLevelNamesMapping"):
        # Python 3.11+, 直接用官方方法
        return logging.getLevelNamesMapping()  # type: ignore
    else:
        # Python <= 3.10, 基于内部变量构造只读映射
        # 用 MappingProxyType 包一层, 避免调用方修改原 dict
        return MappingProxyType(dict(logging._nameToLevel))


def level_range(
    first: int = 0, last: int = 100, levels: Iterable[int] | None = None
) -> set[int]:
    """
    根据给定范围生成Level集合

    参数:
      first: 起始Level数值, 闭区间.
      last: 结束Level者数值, 闭区间.
      levels: 数值Level列表, 默认全部级别.
    返回:
      区间内的Level集合.
    """

    levels = levels or get_level_names_mapping().values()
    return {i for i in levels if i != 0 and first <= i and i <= last}


def get_level(name: str) -> int:
    """
    获取数值形式的等级

    参数:
        name: 字符串形式的等级
    返回:
        数值形式的等级
    异常:
        ValueError: 无此等级时抛出
    """

    mapping = get_level_names_mapping()
    if name not in mapping:
        raise ValueError(f"Unknown level: {name}")
    return mapping[name]
