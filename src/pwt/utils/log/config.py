from __future__ import annotations

import logging
import logging.handlers
import sys
from datetime import datetime
from types import EllipsisType
from typing import Annotated, Literal

from pydantic import Field

from pwt.utils.log import helpers
from pwt.utils.log.filters import FieldFilter
from pwt.utils.pydantic_utils import BaseModelEx, check, convert

OUTPUT_DEFAULT = "std"
OUTPUT_OPTIONS = ("std", "stdout", "stderr")
OUTPUT_TYPE = Literal["std", "stdout", "stderr"]

OUTPUT_FORMAT_DEFAULT = "text"
OUTPUT_FORMAT_TYPE = Literal["text", "json"]

TEXT_FORMAT_DEFAULT = "{asctime} {levelname}: {message}"
DATE_FORMAT_DEFAULT = "%Y-%m-%d %H:%M:%S"

LEVEL_DEFAULT = "INFO"
LEVEL_OPTIONS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")
LEVEL_TYPE = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
LEVEL_VERBOSE = "DEBUG"

FILTERS_DEFAULT = None


class Handler(BaseModelEx):
    output: Annotated[
        str | OUTPUT_TYPE,
        convert(lambda v: vl if (vl := v.lower()) in OUTPUT_OPTIONS else v),
    ] = OUTPUT_DEFAULT
    output_format: Annotated[
        OUTPUT_FORMAT_TYPE,
        convert(str.lower),
    ] = OUTPUT_FORMAT_DEFAULT
    text_format: Annotated[
        str,
        check(lambda value: logging.StrFormatStyle(value).validate()),
    ] = TEXT_FORMAT_DEFAULT
    date_format: Annotated[
        str | None,
        check(datetime.now().strftime),
    ] = DATE_FORMAT_DEFAULT
    level: Annotated[
        LEVEL_TYPE,
        convert(str.upper),
    ] = LEVEL_DEFAULT
    filters: Annotated[
        list[str] | None,
        Field(min_length=1),
        check(str.strip, data_shape="list", check_result=True),
    ] = FILTERS_DEFAULT


class Log(BaseModelEx):
    name: str | None = None
    level: Annotated[
        LEVEL_TYPE,
        convert(str.upper),
    ] = LEVEL_DEFAULT
    filters: Annotated[
        list[str] | None,
        Field(min_length=1),
        check(str.strip, data_shape="list", check_result=True),
    ] = FILTERS_DEFAULT
    propagate: bool = True
    handlers: list[Handler] | None = None


def get_handler(log: Handler) -> logging.Handler:
    """
    根据给定的日志配置列表创建并返回日志处理器列表.

    参数:
        logs (Log): 日志配置的实例.

    返回:
        logging.Handler: 根据配置创建的日志处理器.

    异常:
        FileNotFoundError, PermissionError: 读写文件错误
    """
    if log.output == "std":
        handler = helpers.StandardHandler()
    elif log.output == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    elif log.output == "stderr":
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.handlers.WatchedFileHandler(log.output)

    formatter = helpers.EnhancedFormatter(
        log.text_format,
        log.date_format,
        style="{",
        output_format=log.output_format,
    )
    handler.setFormatter(formatter)

    handler.setLevel(log.level)
    if log.filters is not None:
        handler.addFilter(FieldFilter(*log.filters))
    return handler


def get_logger(
    log: Log, *, logger: logging.Logger | str | None | EllipsisType = ...
) -> logging.Logger:
    if logger is ...:
        logger = logging.getLogger(log.name)
    elif not isinstance(logger, logging.Logger):
        logger = logging.getLogger(logger)

    if log.level is not None:
        logger.setLevel(log.level)

    for f in logger.filters[:]:
        logger.removeFilter(f)
    if log.filters is not None:
        logger.addFilter(FieldFilter(*log.filters))

    logger.propagate = log.propagate

    for h in logger.handlers[:]:
        logger.removeHandler(h)
    if log.handlers is not None:
        for handler in log.handlers:
            logger.addHandler(get_handler(handler))

    return logger
