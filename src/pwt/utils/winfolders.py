"""
提供对 Windows 已知文件夹 (Known Folders) 的访问封装.

该模块通过 ctypes 直接调用 Windows API, 以 GUID 为标识获取系统已知文件夹的路径.
相比使用第三方库, 这种方式更接近底层, 避免了不必要的抽象.

主要功能:
- 定义 Folder 枚举, 包含常见的已知文件夹 GUID.
- 定义 GUID 结构体, 与 Windows API 的 GUID/CLSID 结构兼容.
- 提供 query_folder_path(folder) 函数, 用于查询指定已知文件夹的实际路径.

注意:
- 本模块仅在 Windows 平台可用; 在非 Windows 平台调用会抛出 NotImplementedError.
"""

from __future__ import annotations

import ctypes
import enum
import sys


class Folder(enum.Enum):
    """Windows 已知文件夹 (Known Folders) 的枚举"""

    # fmt: off
    AccountPictures =        "{008ca0b1-55b4-4c56-b8a8-4de4b299d3be}"  # %APPDATA%\Microsoft\Windows\AccountPictures
    AdminTools =             "{724EF170-A42D-4FEF-9F26-B60E846FBA4F}"  # %APPDATA%\Microsoft\Windows\Start Menu\Programs\Administrative Tools
    AppDataDesktop =         "{B2C5E279-7ADD-439F-B28C-C41FE1BBF672}"  # %LOCALAPPDATA%\Desktop
    AppDataDocuments =       "{7BE16610-1F7F-44AC-BFF0-83E15F2FFCA1}"  # %LOCALAPPDATA%\Documents
    AppDataFavorites =       "{7CFBEFBC-DE1F-45AA-B843-A542AC536CC9}"  # %LOCALAPPDATA%\Favorites
    AppDataProgramData =     "{559D40A3-A036-40FA-AF61-84CB430A4D34}"  # %LOCALAPPDATA%\ProgramData
    ApplicationShortcuts =   "{A3918781-E5F2-4890-B3D9-A7E54332328C}"  # %LOCALAPPDATA%\Microsoft\Windows\Application Shortcuts
    CameraRoll =             "{AB5FB87B-7CE2-4F83-915D-550846C9537B}"  # %USERPROFILE%\Pictures\Camera Roll
    CDBurning =              "{9E52AB10-F80D-49DF-ACB8-4330F5687855}"  # %LOCALAPPDATA%\Microsoft\Windows\Burn\Burn
    CommonAdminTools =       "{D0384E7D-BAC3-4797-8F14-CBA229B392B5}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Administrative Tools
    CommonOEMLinks =         "{C1BAE2D0-10DF-4334-BEDD-7AA20B227A9D}"  # %ALLUSERSPROFILE%\OEM Links
    CommonPrograms =         "{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs
    CommonStartMenu =        "{A4115719-D62E-491D-AA7C-E74B8BE3B067}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Start Menu
    CommonStartup =          "{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\StartUp
    CommonTemplates =        "{B94237E7-57AC-4347-9151-B08C6C32D1F7}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Templates
    Contacts =               "{56784854-C6CB-462b-8169-88E350ACB882}"  # %USERPROFILE%\Contacts
    Cookies =                "{2B0F765D-C0E9-4171-908E-08A611B84FF6}"  # %APPDATA%\Microsoft\Windows\Cookies
    Desktop =                "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"  # %USERPROFILE%\Desktop
    DeviceMetadataStore =    "{5CE4A5E9-E4EB-479D-B89F-130C02886155}"  # %ALLUSERSPROFILE%\Microsoft\Windows\DeviceMetadataStore
    Documents =              "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"  # %USERPROFILE%\Documents
    DocumentsLibrary =       "{7B0DB17D-9CD2-4A93-9733-46CC89022E7C}"  # %APPDATA%\Microsoft\Windows\Libraries\Documents.library-ms
    Downloads =              "{374DE290-123F-4565-9164-39C4925E467B}"  # %USERPROFILE%\Downloads
    Favorites =              "{1777F761-68AD-4D8A-87BD-30B759FA33DD}"  # %USERPROFILE%\Favorites
    Fonts =                  "{FD228CB7-AE11-4AE3-864C-16F3910AB8FE}"  # %windir%\Fonts
    GameTasks =              "{054FAE61-4DD8-4787-80B6-090220C4B700}"  # %LOCALAPPDATA%\Microsoft\Windows\GameExplorer
    History =                "{D9DC8A3B-B784-432E-A781-5A1130A75963}"  # %LOCALAPPDATA%\Microsoft\Windows\History
    ImplicitAppShortcuts =   "{BCB5256F-79F6-4CEE-B725-DC34E402FD46}"  # %APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\ImplicitAppShortcuts
    InternetCache =          "{352481E8-33BE-4251-BA85-6007CAEDCF9D}"  # %LOCALAPPDATA%\Microsoft\Windows\Temporary Internet Files
    Libraries =              "{1B3EA5DC-B587-4786-B4EF-BD1DC332AEAE}"  # %APPDATA%\Microsoft\Windows\Libraries
    Links =                  "{bfb9d5e0-c6a9-404c-b2b2-ae6db6af4968}"  # %USERPROFILE%\Links
    LocalAppData =           "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}"  # %LOCALAPPDATA% (%USERPROFILE%\AppData\Local)
    LocalAppDataLow =        "{A520A1A4-1780-4FF6-BD18-167343C5AF16}"  # %USERPROFILE%\AppData\LocalLow
    LocalizedResourcesDir =  "{2A00375E-224C-49DE-B8D1-440DF7EF3DDC}"  # %windir%\resources\0409 (code page)
    Music =                  "{4BD8D571-6D19-48D3-BE97-422220080E43}"  # %USERPROFILE%\Music
    MusicLibrary =           "{2112AB0A-C86A-4FFE-A368-0DE96E47012E}"  # %APPDATA%\Microsoft\Windows\Libraries\Music.library-ms
    NetHood =                "{C5ABBF53-E17F-4121-8900-86626FC2C973}"  # %APPDATA%\Microsoft\Windows\Network Shortcuts
    Objects3D =              "{31C0DD25-9439-4F12-BF41-7FF4EDA38722}"  # %USERPROFILE%\3D Objects
    OriginalImages =         "{2C36C0AA-5812-4b87-BFD0-4CD0DFB19B39}"  # %LOCALAPPDATA%\Microsoft\Windows Photo Gallery\Original Images
    PhotoAlbums =            "{69D2CF90-FC33-4FB7-9A0C-EBB0F0FCB43C}"  # %USERPROFILE%\Pictures\Slide Shows
    PicturesLibrary =        "{A990AE9F-A03B-4E80-94BC-9912D7504104}"  # %APPDATA%\Microsoft\Windows\Libraries\Pictures.library-ms
    Pictures =               "{33E28130-4E1E-4676-835A-98395C3BC3BB}"  # %USERPROFILE%\Pictures
    Playlists =              "{DE92C1C7-837F-4F69-A3BB-86E631204A23}"  # %USERPROFILE%\Music\Playlists
    PrintHood =              "{9274BD8D-CFD1-41C3-B35E-B13F55A758F4}"  # %APPDATA%\Microsoft\Windows\Printer Shortcuts
    Profile =                "{5E6C858F-0E22-4760-9AFE-EA3317B67173}"  # %USERPROFILE% (%SystemDrive%\Users\%USERNAME%)
    ProgramData =            "{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}"  # %ALLUSERSPROFILE% (%ProgramData%, %SystemDrive%\ProgramData)
    ProgramFiles =           "{905e63b6-c1bf-494e-b29c-65b732d3d21a}"  # %ProgramFiles% (%SystemDrive%\Program Files)
    ProgramFilesX64 =        "{6D809377-6AF0-444b-8957-A3773F02200E}"  # %ProgramFiles% (%SystemDrive%\Program Files)
    ProgramFilesX86 =        "{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}"  # %ProgramFiles% (%SystemDrive%\Program Files (x86))
    ProgramFilesCommon =     "{F7F1ED05-9F6D-47A2-AAAE-29D317C6F066}"  # %ProgramFiles%\Common Files
    ProgramFilesCommonX64 =  "{6365D5A7-0F0D-45E5-87F6-0DA56B6A4F7D}"  # %ProgramFiles%\Common Files
    ProgramFilesCommonX86 =  "{DE974D24-D9C6-4D3E-BF91-F4455120B917}"  # %ProgramFiles%\Common Files
    Programs =               "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"  # %APPDATA%\Microsoft\Windows\Start Menu\Programs
    Public =                 "{DFDF76A2-C82A-4D63-906A-5644AC457385}"  # %PUBLIC% (%SystemDrive%\Users\Public)
    PublicDesktop =          "{C4AA340D-F20F-4863-AFEF-F87EF2E6BA25}"  # %PUBLIC%\Desktop
    PublicDocuments =        "{ED4824AF-DCE4-45A8-81E2-FC7965083634}"  # %PUBLIC%\Documents
    PublicDownloads =        "{3D644C9B-1FB8-4f30-9B45-F670235F79C0}"  # %PUBLIC%\Downloads
    PublicGameTasks =        "{DEBF2536-E1A8-4c59-B6A2-414586476AEA}"  # %ALLUSERSPROFILE%\Microsoft\Windows\GameExplorer
    PublicLibraries =        "{48DAF80B-E6CF-4F4E-B800-0E69D84EE384}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Libraries
    PublicMusic =            "{3214FAB5-9757-4298-BB61-92A9DEAA44FF}"  # %PUBLIC%\Music
    PublicPictures =         "{B6EBFB86-6907-413C-9AF7-4FC2ABF07CC5}"  # %PUBLIC%\Pictures
    PublicRingtones =        "{E555AB60-153B-4D17-9F04-A5FE99FC15EC}"  # %ALLUSERSPROFILE%\Microsoft\Windows\Ringtones
    PublicUserTiles =        "{0482af6c-08f1-4c34-8c90-e17ec98b1e17}"  # %PUBLIC%\AccountPictures
    PublicVideos =           "{2400183A-6185-49FB-A2D8-4A392A602BA3}"  # %PUBLIC%\Videos
    QuickLaunch =            "{52a4f021-7b75-48a9-9f6b-4b87a210bc8f}"  # %APPDATA%\Microsoft\Internet Explorer\Quick Launch
    Recent =                 "{AE50C081-EBD2-438A-8655-8A092E34987A}"  # %APPDATA%\Microsoft\Windows\Recent
    RecordedTVLibrary =      "{1A6FDBA2-F42D-4358-A798-B74D745926C5}"  # %PUBLIC%\RecordedTV.library-ms
    ResourceDir =            "{8AD10C31-2ADB-4296-A8F7-E4701232C972}"  # %windir%\Resources
    Ringtones =              "{C870044B-F49E-4126-A9C3-B52A1FF411E8}"  # %LOCALAPPDATA%\Microsoft\Windows\Ringtones
    RoamingAppData =         "{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}"  # %APPDATA% (%USERPROFILE%\AppData\Roaming)
    RoamedTileImages =       "{AAA8D5A5-F1D6-4259-BAA8-78E7EF60835E}"  # %LOCALAPPDATA%\Microsoft\Windows\RoamedTileImages
    RoamingTiles =           "{00BCFC5A-ED94-4e48-96A1-3F6217F21990}"  # %LOCALAPPDATA%\Microsoft\Windows\RoamingTiles
    SavedGames =             "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}"  # %USERPROFILE%\Saved Games
    SavedPictures =          "{3B193882-D3AD-4eab-965A-69829D1FB59F}"  # %USERPROFILE%\Pictures\Saved Pictures
    SavedPicturesLibrary =   "{E25B5812-BE88-4bd9-94B0-29233477B6C3}"  # %APPDATA%\Microsoft\Windows\Libraries\SavedPictures.library-ms
    SavedSearches =          "{7d1d3a04-debb-4115-95cf-2f29da2920da}"  # %USERPROFILE%\Searches
    Screenshots =            "{b7bede81-df94-4682-a7d8-57a52620b86f}"  # %USERPROFILE%\Pictures\Screenshots
    SearchHistory =          "{0D4C3DB6-03A3-462F-A0E6-08924C41B5D4}"  # %LOCALAPPDATA%\Microsoft\Windows\ConnectedSearch\History
    SearchTemplates =        "{7E636BFE-DFA9-4D5E-B456-D7B39851D8A9}"  # %LOCALAPPDATA%\Microsoft\Windows\ConnectedSearch\Templates
    SendTo =                 "{8983036C-27C0-404B-8F08-102D10DCFD74}"  # %APPDATA%\Microsoft\Windows\SendTo
    SkyDrive =               "{A52BBA46-E9E1-435f-B3D9-28DAA648C0F6}"  # %USERPROFILE%\OneDrive
    SkyDriveCameraRoll =     "{767E6811-49CB-4273-87C2-20F355E1085B}"  # %USERPROFILE%\OneDrive\Pictures\Camera Roll
    SkyDriveDocuments =      "{24D89E24-2F19-4534-9DDE-6A6671FBB8FE}"  # %USERPROFILE%\OneDrive\Documents
    SkyDrivePictures =       "{339719B5-8C47-4894-94C2-D8F77ADD44A6}"  # %USERPROFILE%\OneDrive\Pictures
    StartMenu =              "{625B53C3-AB48-4EC1-BA1F-A1EF4146FC19}"  # %APPDATA%\Microsoft\Windows\Start Menu
    Startup =                "{B97D20BB-F46A-4C97-BA10-5E3608430854}"  # %APPDATA%\Microsoft\Windows\Start Menu\Programs\StartUp
    System =                 "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"  # %windir%\system32
    SystemX86 =              "{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}"  # %windir%\system32
    Templates =              "{A63293E8-664E-48DB-A079-DF759E0509F7}"  # %APPDATA%\Microsoft\Windows\Templates
    UserPinned =             "{9E3995AB-1F9C-4F13-B827-48B24B6C7174}"  # %APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned
    UserProfiles =           "{0762D272-C50A-4BB0-A382-697DCD729B80}"  # %SystemDrive%\Users
    UserProgramFiles =       "{5CD7AEE2-2219-4A67-B85D-6C9CE15660CB}"  # %LOCALAPPDATA%\Programs
    UserProgramFilesCommon = "{BCBD3057-CA5C-4622-B42D-BC56DB0AE516}"  # %LOCALAPPDATA%\Programs\Common
    Videos =                 "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}"  # %USERPROFILE%\Videos
    VideosLibrary =          "{491E922F-5643-4AF4-A7EB-4E7A138D8174}"  # %APPDATA%\Microsoft\Windows\Libraries\Videos.library-ms
    Windows =                "{F38BF404-1D43-42F2-9305-67DE0B28FC23}"  # %windir%
    # fmt: on


class GUID(ctypes.Structure):
    """Windows API 兼容的 GUID 结构体"""

    _fields_ = [
        ("Data1", ctypes.c_uint32),  # DWORD
        ("Data2", ctypes.c_uint16),  # WORD
        ("Data3", ctypes.c_uint16),  # WORD
        ("Data4", ctypes.c_ubyte * 8),  # BYTE[8]
    ]


# 声明函数签名
if sys.platform == "win32":
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),  # [in] REFKNOWNFOLDERID rfid
        ctypes.c_uint32,  # [in] DWORD dwFlags
        ctypes.c_void_p,  # [in, optional] HANDLE hToken
        ctypes.POINTER(ctypes.c_wchar_p),  # [out] PWSTR *ppszPath
    ]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long  # HRESULT

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CLSIDFromString.argtypes = [
        ctypes.c_wchar_p,  # [in] LPCOLESTR lpsz
        ctypes.POINTER(GUID),  # [out] LPCLSID pclsid
    ]
    ole32.CLSIDFromString.restype = ctypes.c_long  # HRESULT
    ole32.CoTaskMemFree.argtypes = [
        ctypes.c_void_p,  # [in, optional] LPVOID pv
    ]
    ole32.CoTaskMemFree.restype = None  # void
else:

    class _WinNotAvailable:
        def __getattr__(self, name):
            raise NotImplementedError("win_folders is only supported on Windows")

    shell32 = _WinNotAvailable()
    ole32 = _WinNotAvailable()


def query_folder_path(folder: Folder) -> str:
    """
    查询指定 Windows 已知文件夹的实际路径.

    此函数通过 Windows API 的 SHGetKnownFolderPath 函数获取指定已知文件夹的完整路径.
    已知文件夹是 Windows 系统中预定义的特殊文件夹, 如桌面/文档/下载等.

    参数:
        folder (Folder): Folder 枚举值, 表示要查询的已知文件夹类型.
                        例如: Folder.Desktop/Folder.Documents/Folder.Downloads 等.
    返回:
        str: 所请求文件夹的完整路径字符串.
    异常:
        OSError: 当 Windows API 调用失败时抛出, 包含具体的 HRESULT 错误代码.
        NotImplementedError: 在非 Windows 平台上调用时抛出.
    """
    guid = GUID()
    hresult = ole32.CLSIDFromString(folder.value, ctypes.byref(guid))
    if hresult != 0:
        error_code = hresult & 0xFFFFFFFF
        raise OSError(f"CLSIDFromString failed, HRESULT=0x{error_code:08X}")

    p_path = ctypes.c_wchar_p()
    hresult = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid),
        0x00004000,  # KF_FLAG_DONT_VERIFY
        None,
        ctypes.byref(p_path),
    )
    try:
        if hresult != 0:
            error_code = hresult & 0xFFFFFFFF
            raise OSError(f"SHGetKnownFolderPath failed, HRESULT=0x{error_code:08X}")
        return p_path.value  # type: ignore
    finally:
        ole32.CoTaskMemFree(p_path)
