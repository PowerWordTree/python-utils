from __future__ import annotations

import sys
from pathlib import Path


def find_project_root(
    start: Path | str = Path(__file__),
    markers: tuple[str, ...] = ("pyproject.toml", "setup.py", ".project_root"),
    max_depth: int = 5,
    default: Path | str | None = None,
) -> Path | None:
    """
    查找项目根目录。

    该函数从起始位置开始向上查找特定的标记文件，直到找到项目根目录或达到最大搜索深度。
    如果代码被打包为可执行文件，则返回可执行文件所在的目录。

    Args:
        start: 搜索的起始路径，默认为当前文件所在目录。
        markers: 用于标识项目根目录的文件名元组，
            默认为 ("pyproject.toml", "setup.py", ".project_root")。
        max_depth: 向上搜索的最大深度，默认为 5。
        default: 如果未找到项目根目录，则返回的默认路径，默认为 None。

    Returns:
        Path | None: 找到的项目根目录路径，如果未找到且未提供默认值则返回 None。
    """
    # 打包后的情况
    if getattr(sys, "frozen", False):
        return Path(sys.executable).absolute().parent
    # 源码运行情况
    start = Path(start).absolute()
    for parent in (start, *start.parents[:max_depth]):
        if any((parent / marker).exists() for marker in markers):
            return parent
    # fallback：返回默认值
    return Path(default) if default is not None else None
