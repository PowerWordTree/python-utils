from __future__ import annotations

import logging
import sys
from typing import Any

from pwt.utils.log.helpers import EnhancedFormatter, FmtLoggerAdapter
from rich.console import ConsoleRenderable, RenderableType
from rich.logging import RichHandler
from rich.text import Text


def get_sytled_logger_adapter(name: str | None = None) -> StyledLoggerAdapter:
    return StyledLoggerAdapter(logging.getLogger(name))


def get_sytled_standard_logger_adapter(
    name: str | None = None,
    spacing: RenderableType | str | None = "",
    show_time: bool = False,
    show_level: bool = False,
    keywords: list[str] | None = None,
) -> StyledLoggerAdapter:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = StyledStandardHandler(spacing, show_time, show_level, keywords)
    formatter = EnhancedFormatter(textfmt="{message}")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return StyledLoggerAdapter(logger)


class StyledStandardHandler(RichHandler):
    def __init__(
        self,
        spacing: RenderableType | str | None = "",
        show_time: bool = False,
        show_level: bool = False,
        keywords: list[str] | None = None,
    ) -> None:
        super().__init__(
            show_time=show_time,
            show_level=show_level,
            show_path=False,
            markup=False,
            rich_tracebacks=False,
            log_time_format="%Y-%m-%d %H:%M:%S",
            keywords=keywords,
        )

        self.spacing = spacing
        self.last_section = None
        self.show_level = show_level
        self._stdout_isatty = sys.stdout.isatty()
        self._stderr_isatty = sys.stderr.isatty()

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            self.console.file = sys.stdout
            isatty = self._stdout_isatty
        else:
            self.console.file = sys.stderr
            isatty = self._stderr_isatty

        section = getattr(record, "logSection", None)
        if isatty and self.spacing is not None and self.last_section != section:
            self.console.print(self.spacing)
        self.last_section = section

        super().emit(record)

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        text = super().render_message(record, message)

        if not self.show_level and isinstance(text, Text):
            if record.levelno == logging.DEBUG:
                text.stylize("dim")
            # elif record.levelno == logging.INFO:
            #     text.stylize("white")
            elif record.levelno == logging.WARNING:
                text.stylize("yellow")
            elif record.levelno == logging.ERROR:
                text.stylize("red")
            elif record.levelno == logging.CRITICAL:
                text.stylize("bold white on red")

        return text


class StyledLoggerAdapter(FmtLoggerAdapter):
    def __init__(self, logger: logging.Logger, **extra: Any) -> None:
        super().__init__(logger, **extra)

    def log_section(self, section: Any) -> None:
        logger = self.target
        while logger:
            for handler in logger.handlers:
                if isinstance(handler, StyledStandardHandler):
                    handler.last_section = section
            if not logger.propagate:
                break
            else:
                logger = logger.parent
