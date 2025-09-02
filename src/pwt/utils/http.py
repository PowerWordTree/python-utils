import re
from typing import Any
from requests import Session, Response, exceptions

from pwt.utils.decorator import Decorator
from pwt.utils.log import log_helpers

logger = log_helpers.get_logger_adapter(__name__)

class LogRequestsException(Decorator):
    """
    装饰器 - 输出 RequestException 的 WARNING 日志
    """

    def wrapper(self, *args: Any, **kwds: Any) -> Any:
        """
        为装饰方法添加异常日志
        """

        try:
            result = super().wrapper(*args, **kwds)
            return result
        except exceptions.RequestException as ex:
            if hasattr(ex, "log_request_exception"):
                raise ex
            setattr(ex, "log_request_exception", True)
            match ex:
                case exceptions.HTTPError():
                    logger.warning(f"Http - HTTP错误 - {ex}")
                case exceptions.ConnectionError() | exceptions.Timeout():
                    logger.warning(f"Http - 连接错误 - {ex}")
                case exceptions.URLRequired() | exceptions.MissingSchema():
                    logger.warning(f"Http - URL错误 - {ex}")
                case exceptions.TooManyRedirects():
                    logger.warning(f"Http - 太多重定向 - {ex}")
                case exceptions.InvalidSchema():
                    logger.warning(f"Http - 无效模式 - {ex}")
                case exceptions.InvalidURL():
                    logger.warning(f"Http - 无效的URL - {ex}")
                case exceptions.InvalidHeader():
                    logger.warning(f"Http - 无效的Header - {ex}")
                case exceptions.ChunkedEncodingError():
                    logger.warning(f"Http - 分块编码错误 - {ex}")
                case exceptions.ContentDecodingError():
                    logger.warning(f"Http - 内容解码错误 - {ex}")
                case exceptions.JSONDecodeError():
                    logger.warning(f"Http - JSON解码错误 - {ex}")
                case exceptions.StreamConsumedError():
                    logger.warning(f"Http - 流消耗错误 - {ex}")
                case exceptions.RetryError():
                    logger.warning(f"Http - 重试错误 - {ex}")
                case exceptions.UnrewindableBodyError():
                    logger.warning(f"Http - 无法追踪正文 - {ex}")
                case exceptions.FileModeWarning():
                    logger.warning(f"Http - 文件模式警告 - {ex}")
                case exceptions.RequestsDependencyWarning():
                    logger.warning(f"Http - 依赖警告 - {ex}")
                case _:
                    logger.warning(f"Http - 其它警告 - {ex}")
            raise ex


class Http(Session):

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._headers = {
            "Referer": base_url,
            "User-Agent": "Mozilla/ 5.0(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, Like Gecko) "
            "Chrome/93.0.4577.82 Safari/537.36 Edg/93.0.961.52",
        }
        self.headers.update(self._headers)

    @LogRequestsException
    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:
        url = self.base_url + url
        kwargs.setdefault("timeout", (3.05, 27))  # 超时时间(连接超时,读取超时)
        logger.debug(
            f"Http - 发起请求 - {method.upper()} - {url} - {kwargs.get('params')}"
            f" - {kwargs.get('data') or kwargs.get('json')}"
        )
        response = super().request(method, url, *args, **kwargs)
        logger.debug(f"Http - 收到响应 - {self._logtext_history_status(response)}")
        response.raise_for_status()
        logger.debug(
            f"Http - 请求成功 - {response.elapsed} - {response.headers.get('Content-Type')}"
            f" - {format(len(response.content), ',')}"  # 读取content可能引发异常
        )
        return response

    @LogRequestsException
    def text(self, url: str, *args: Any, **kwargs: Any) -> str:
        response = self.get(url, *args, **kwargs)
        logger.debug(
            f"Http - 开始获取文本 - {format(len(response.content), ',')}"
            f" - {self._truncate_middle(response.content, 200)}"
        )
        text = response.text
        logger.debug(
            f"Http - 获取文本成功 - {format(len(text), ',')}"
            f" - {self._truncate_middle(text, 200)}"
        )
        return text

    @LogRequestsException
    def json(self, url: str, *args: Any, **kwargs: Any) -> dict:
        response = self.post(url, *args, **kwargs)
        logger.debug(
            f"Http - 开始Json解析 - {format(len(response.content), ',')}"
            f" - {self._truncate_middle(response.content, 200)}"
        )
        json = response.json()
        logger.debug(
            f"Http - 解析Json完成 - {format(len(json), ',')}"
            f" - {self._truncate_middle(json, 200)}"
        )
        return json

    def _logtext_history_status(self, response: Response) -> str:
        """
        展示http请求的跳转路径信息

        参数:
            response: 响应对象
        返回:
            请求跳转路径的信息字符串
                格式: 方法 - 地址 - 状态码 - 状态文本 => ...
        """

        history = response.history[:]
        history.append(response)
        return " => ".join(
            f"{r.request.method} - {r.request.url} - {r.status_code} - {r.reason}"
            for r in history
        )

    def _truncate_middle(self, obj: Any, length: int) -> str:
        """
        字符串内部截断

        参数:
            obj: 提供字符串的对象
            length: 长度
        返回:
            根据给定长度从字符串内部截断, 并添加` ... `作为分隔符.
                string: "abcdefghijkijklmnopqrst"    length: 10
                out: "abc ... st"
        """

        if length <= 5:
            return " ... "
        text = re.sub(r"\s*[\r\n]\s*", "", str(obj)).strip()
        if len(text) > length:
            begin_len = end_len = (length - 5) // 2
            begin_len += (length - 5) % 2
            text = text[:begin_len] + " ... " + text[-end_len:]
        return text
