import logging
import sys

from rich.console import ConsoleRenderable, RenderableType
from rich.logging import RichHandler
from rich.text import Text

from pwt.utils.log.log_helpers import EnhancedFormatter, FmtLoggerAdapter


def get_sytled_standard_logger_adapter(
    name: str | None = None,
    spacing: RenderableType | str | None = "",
    show_time: bool = False,
    show_level: bool = False,
    keywords: list[str] | None = None,
) -> FmtLoggerAdapter:
    """
    获取风格化的日志记录器并进行基本配置.

    参数:
        name (str | None): 日志记录器的名称.
        spacing (RenderableType | str | None): 段落分隔符,
        show_time (bool): 是否显示时间.
        show_level (bool): 是否显示日志级别.
        keywords (list[str] | None): 关键词列表.

    返回:
        logging.Logger: 配置好的日志记录器.
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = StyledStandardHandler(spacing, show_time, show_level, keywords)
    formatter = EnhancedFormatter(textfmt="{message}")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return FmtLoggerAdapter(logger)


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
