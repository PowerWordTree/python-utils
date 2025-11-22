"""
使用 ctypes 绑定 advapi32, 提供常见 SID 的创建与成员检查

仅在 Windows 上可用; 非 Windows 调用会抛出 NotImplementedError.

主要组件:
- Principal: 定义常见 Well-Known SIDs
- create_sid: 以 contextmanager 创建并自动释放 SID.
- check_membership: 判断当前令牌是否属于某个 Principal.
- is_xxx: 是 check_membership 的快捷方法, 返回 bool 值.

快速示例:
  >>> from win_security import check_membership, Principal
  >>> check_membership(Principal.ADMINISTRATORS)
  True  # 若当前令牌属于 Administrators

  >>> from win_security import create_sid
  >>> from contextlib import closing
  >>> with create_sid(Principal.EVERYONE) as sid:
  ...     # 在 with 内使用 sid; 退出时自动调用 FreeSid 释放
  ...     pass
"""

import ctypes
import ctypes.wintypes
import enum
import sys
from contextlib import contextmanager
from typing import Iterator

NT_AUTHORITY = (ctypes.wintypes.BYTE * 6)(0, 0, 0, 0, 0, 5)
WORLD_AUTHORITY = (ctypes.wintypes.BYTE * 6)(0, 0, 0, 0, 0, 1)


class Principal(enum.Enum):
    """
    常见 Well-Known SID 的枚举定义

    每项由:
    - authority: 6 字节标识符权限
    - subs: 子权限列表(最多 8 个, 用 0 填充)
    """

    # fmt: off
    ADMINISTRATORS      = NT_AUTHORITY, [32, 544]   # BUILTIN\Administrators
    USERS               = NT_AUTHORITY, [32, 545]   # BUILTIN\Users
    GUESTS              = NT_AUTHORITY, [32, 546]   # BUILTIN\Guests
    POWER_USERS         = NT_AUTHORITY, [32, 547]   # BUILTIN\Power Users

    SYSTEM              = NT_AUTHORITY, [18]        # LocalSystem
    LOCAL_SERVICE       = NT_AUTHORITY, [19]        # LocalService
    NETWORK_SERVICE     = NT_AUTHORITY, [20]        # NetworkService

    EVERYONE            = WORLD_AUTHORITY, [0]      # Everyone
    AUTHENTICATED_USERS = NT_AUTHORITY, [11]        # Authenticated Users
    INTERACTIVE         = NT_AUTHORITY, [4]         # Interactive logon
    NETWORK             = NT_AUTHORITY, [2]         # Network logon
    # fmt: on

    def __init__(self, authority, subs):
        self.authority = authority
        self.sub_count = ctypes.wintypes.BYTE(len(subs))
        self.sub_authorities = tuple(
            ctypes.wintypes.DWORD(x) for x in subs + [0] * (8 - len(subs))
        )


# 声明函数签名
if sys.platform == "win32":
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    # fmt: off
    advapi32.AllocateAndInitializeSid.argtypes = [
            ctypes.POINTER(ctypes.c_byte * 6),  # pIdentifierAuthority
            ctypes.wintypes.BYTE,               # nSubAuthorityCount
            ctypes.wintypes.DWORD,              # nSubAuthority0
            ctypes.wintypes.DWORD,              # nSubAuthority1
            ctypes.wintypes.DWORD,              # nSubAuthority2
            ctypes.wintypes.DWORD,              # nSubAuthority3
            ctypes.wintypes.DWORD,              # nSubAuthority4
            ctypes.wintypes.DWORD,              # nSubAuthority5
            ctypes.wintypes.DWORD,              # nSubAuthority6
            ctypes.wintypes.DWORD,              # nSubAuthority7
            ctypes.POINTER(ctypes.c_void_p)     # pSid
        ]
    advapi32.AllocateAndInitializeSid.restype = ctypes.wintypes.BOOL

    advapi32.CheckTokenMembership.argtypes = [
            ctypes.wintypes.HANDLE,              # TokenHandle
            ctypes.c_void_p,                     # SidToCheck
            ctypes.POINTER(ctypes.wintypes.BOOL) # IsMember
        ]
    advapi32.CheckTokenMembership.restype = ctypes.wintypes.BOOL

    advapi32.FreeSid.argtypes = [ctypes.c_void_p]
    advapi32.FreeSid.restype = ctypes.c_void_p
    # fmt: on
else:

    class _WinNotAvailable:
        def __getattr__(self, name):
            raise NotImplementedError("win_security is only supported on Windows")

    advapi32 = _WinNotAvailable()


@contextmanager
def create_sid(principal: Principal) -> Iterator[ctypes.c_void_p]:
    """
    以 contextmanager 创建并托管一个 SID

    进入时调用 AllocateAndInitializeSid, 退出时调用 FreeSid, 确保资源正确释放.

    Args:
        principal: 要创建 SID 的 Principal 枚举值

    Yields:
        ctypes.c_void_p: 创建的 SID 指针

    Raises:
        OSError: 当 SID 创建失败时, 包含 Windows 错误代码
    """
    sid = ctypes.c_void_p()
    success = advapi32.AllocateAndInitializeSid(
        ctypes.byref(principal.authority),
        principal.sub_count,
        *principal.sub_authorities,
        ctypes.byref(sid),
    )
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        yield sid
    finally:
        advapi32.FreeSid(sid)


def check_membership(principal: Principal) -> bool:
    """
    检查当前进程令牌是否属于指定 Principal

    此函数检查当前进程的安全令牌是否属于指定的安全组或用户.

    Args:
        principal: 要检查的 Principal 枚举值

    Returns:
        bool: 如果当前令牌属于指定的 Principal, 返回 True; 否则返回 False

    Raises:
        OSError: 当检查成员资格失败时, 包含 Windows 错误代码
    """
    with create_sid(principal) as sid:
        is_member = ctypes.wintypes.BOOL()
        success = advapi32.CheckTokenMembership(None, sid, ctypes.byref(is_member))
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        return bool(is_member.value)


def is_system() -> bool:
    """
    是否属于 LocalSystem(SYSTEM)
    """
    return check_membership(Principal.SYSTEM)


def is_admin() -> bool:
    """
    是否属于 BUILTIN\\Administrators
    """
    return check_membership(Principal.ADMINISTRATORS)


def is_user() -> bool:
    """
    是否属于 BUILTIN\\Users
    """
    return check_membership(Principal.USERS)


def is_guest() -> bool:
    """
    是否属于 BUILTIN\\Guests
    """
    return check_membership(Principal.GUESTS)
