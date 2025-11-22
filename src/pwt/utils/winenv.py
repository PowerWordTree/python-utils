# ---------------------------------------------------------------------------
# 命名对照表(内部约定 vs Python winreg)
#
# 我们内部使用的命名体系:
#   hreg   → 注册表位置句柄(既可以是根常量 HKEY_*, 也可以是 OpenKeyEx 返回的句柄)
#   root   → 特殊的 hreg, 专指预定义的根常量 (HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE 等)
#   path   → 子路径字符串 (winreg 的 sub_key)
#   key    → 值的名字 (winreg 的 value_name)
#   type   → 值的类型 (winreg 的 type, 例如 REG_SZ, REG_DWORD)
#   value  → 值的数据 (winreg 的 value)
#
# Python winreg / WinAPI 的对应关系:
#   hreg   = 打开的句柄 (WinAPI 的 phkResult), 也可以是 root
#   root   = HKEY_* 常量 (WinAPI 的 hKey 参数) → 也是一种 hreg
#   path   = sub_key
#   key    = value_name
#   type   = type
#   value  = value
#
# 约定:
#   - root 是 hreg 的一个子集(预定义常量)
#   - hreg 表示"注册表位置句柄", 既可能是 root, 也可能是 OpenKeyEx 打开的句柄
#   - 避免用 "key" 表示句柄, 以免和 value_name 混淆
# ---------------------------------------------------------------------------

from __future__ import annotations

import re
import sys
from enum import Enum
from typing import TypeVar, overload

if sys.platform == "win32":
    import winreg
else:

    class _WinNotAvailable:
        def __getattr__(self, name):
            raise NotImplementedError("Not supported on non-Windows platforms")

    winreg = _WinNotAvailable()


class Scope(Enum):
    MACHINE = (
        "HKEY_LOCAL_MACHINE",
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    )
    USER = ("HKEY_CURRENT_USER", r"Environment")

    def __init__(self, root: str, path: str) -> None:
        super().__init__()
        self.root = root
        self.path = path


HAS_VAR_REGEX = re.compile(r"%[^%:=\s]+%")
ERROR_NO_MORE_ITEMS = 259

T = TypeVar("T")


class WinEnv:
    """Windows 环境变量管理类. 

    提供对 Windows 系统环境变量的读取和修改功能, 支持用户级别和系统级别的环境变量操作. 
    该类实现了上下文管理器协议, 可以使用 with 语句自动管理注册表句柄的生命周期. 

    示例:
        with WinEnv(scope="user") as env:
            # 查询环境变量
            path = env.query("PATH")
            # 修改环境变量
            env.replace("PATH", f"{path};C:\\NewPath")
    """

    def __init__(self, scope: Scope = Scope.USER, writable: bool = True) -> None:
        """初始化 WinEnv 实例. 

        Args:
            scope: 环境变量的作用域
            writable: 是否以可写模式打开注册表, True 表示可读写, False 表示只读
        """
        self.scope = scope
        # 打开注册表句柄
        self.hreg = winreg.OpenKeyEx(
            getattr(winreg, scope.root),
            scope.path,
            0,
            (winreg.KEY_READ | winreg.KEY_WRITE) if writable else winreg.KEY_READ,
        )

    def __enter__(self) -> WinEnv:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """关闭注册表句柄. 

        释放由 OpenKeyEx 打开的注册表句柄资源. 
        """
        winreg.CloseKey(self.hreg)

    def enum(self) -> dict[str, str]:
        """枚举所有环境变量. 

        Returns:
            包含所有环境变量名和值的字典
        """
        result = {}
        index = 0
        while True:
            try:
                key, value, _ = winreg.EnumValue(self.hreg, index)
                result[key] = str(value)
                index += 1
            except OSError as exc:
                if getattr(exc, "winerror", None) == ERROR_NO_MORE_ITEMS:
                    break
                raise
        return result

    @overload
    def query(self, key: str) -> str: ...
    @overload
    def query(self, key: str, default: T) -> str | T: ...
    def query(self, key: str, default: object = ...) -> str | object:
        """查询指定的环境变量值. 

        Args:
            key: 环境变量名
            default: 当环境变量不存在时的默认值, 如果未提供且环境变量不存在则抛出异常

        Returns:
            str: 如果变量存在
            default: 如果变量不存在且提供了 default

        Raises:
            FileNotFoundError: 当环境变量不存在且未提供默认值时
        """
        try:
            value, _ = winreg.QueryValueEx(self.hreg, key)
        except FileNotFoundError:
            if default is ...:
                raise
            return default
        return str(value)

    def replace(self, key: str, value: str) -> None:
        """替换指定的环境变量值. 

        如果值中包含环境变量引用(如 %PATH%), 则使用 REG_EXPAND_SZ 类型, 
        否则使用 REG_SZ 类型. 

        Args:
            key: 环境变量名
            value: 新的环境变量值
        """
        if HAS_VAR_REGEX.search(value):
            reg_type = winreg.REG_EXPAND_SZ
        else:
            reg_type = winreg.REG_SZ
        winreg.SetValueEx(self.hreg, key, 0, reg_type, value)

    def suffix(self, key: str, value: str) -> None:
        """在环境变量值的末尾追加内容. 

        Args:
            key: 环境变量名
            value: 要追加的内容
        """
        old_value = self.query(key, default="")
        self.replace(key, f"{old_value!s}{value!s}")

    def prefix(self, key: str, value: str) -> None:
        """在环境变量值的前面添加内容. 

        Args:
            key: 环境变量名
            value: 要添加的内容
        """
        old_value = self.query(key, default="")
        self.replace(key, f"{value!s}{old_value!s}")

    def remove(self, key: str) -> str | None:
        """删除指定的环境变量. 

        Args:
            key: 要删除的环境变量名

        Returns:
            str | None: 如果变量存在, 返回 原值;
                        如果变量不存在, 返回 None;
        """
        old_value = self.query(key, default=None)
        winreg.DeleteValue(self.hreg, key)
        return old_value

    def clear(self) -> None:
        """清除所有环境变量. 

        删除当前作用域中的所有环境变量, 请谨慎使用此方法. 
        """
        while True:
            try:
                name, _, _ = winreg.EnumValue(self.hreg, 0)
                winreg.DeleteValue(self.hreg, name)
            except OSError as exc:
                if getattr(exc, "winerror", None) == ERROR_NO_MORE_ITEMS:
                    break
                raise


def winenv_enum(scope: Scope) -> dict[str, str]:
    """枚举所有环境变量. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域

    Returns:
        包含所有环境变量名和值的字典
    """
    with WinEnv(scope, writable=False) as winenv:
        return winenv.enum()


@overload
def winenv_query(scope: Scope, key: str) -> str: ...
@overload
def winenv_query(scope: Scope, key: str, default: T) -> str | T: ...
def winenv_query(scope: Scope, key: str, default: object = ...) -> str | object:
    """查询指定的环境变量值. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
        key: 环境变量名
        default: 当环境变量不存在时的默认值, 如果未提供且环境变量不存在则抛出异常

    Returns:
        str: 如果变量存在
        default: 如果变量不存在且提供了 default

    Raises:
        FileNotFoundError: 当环境变量不存在且未提供默认值时
    """
    with WinEnv(scope, writable=False) as winenv:
        return winenv.query(key, default)


def winenv_replace(scope: Scope, key: str, value: str) -> None:
    """替换指定的环境变量值. 

    如果值中包含环境变量引用(如 %PATH%), 则使用 REG_EXPAND_SZ 类型, 
    否则使用 REG_SZ 类型. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
        key: 环境变量名
        value: 新的环境变量值
    """
    with WinEnv(scope) as winenv:
        winenv.replace(key, value)


def winenv_suffix(scope: Scope, key: str, value: str) -> None:
    """在环境变量值的末尾追加内容. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
        key: 环境变量名
        value: 要追加的内容
    """
    with WinEnv(scope) as winenv:
        winenv.suffix(key, value)


def winenv_prefix(scope: Scope, key: str, value: str) -> None:
    """在环境变量值的前面添加内容. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
        key: 环境变量名
        value: 要添加的内容
    """
    with WinEnv(scope) as winenv:
        winenv.prefix(key, value)


def winenv_remove(scope: Scope, key: str) -> str | None:
    """删除指定的环境变量. 

    删除当前作用域中的指定环境变量, 请谨慎使用此方法. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
        key: 要删除的环境变量名

    Returns:
        str | None: 如果变量存在, 返回 原值;
                    如果变量不存在, 返回 None;
    """
    with WinEnv(scope) as winenv:
        return winenv.remove(key)


def winenv_clear(scope: Scope) -> None:
    """清除所有环境变量. 

    删除当前作用域中的所有环境变量, 请谨慎使用此方法. 

    快捷入口, 每次调用会重新打开和关闭注册表句柄, 适合一次性操作, 不适合高频调用. 

    Args:
        scope: 环境变量的作用域
    """
    with WinEnv(scope) as winenv:
        winenv.clear()
