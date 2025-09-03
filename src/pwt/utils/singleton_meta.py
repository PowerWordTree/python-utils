"""
线程安全的单例模式元类实现

使用本元类作为 metaclass, 可以让对应类在全局范围内只存在唯一实例,
并且支持惰性初始化(第一次调用时才创建实例), 无初始化参数.
"""

import threading


class SingletonMeta(type):
    """
    线程安全的单例元类.

    特性:
        - 所有使用此元类的类只会创建一个实例
        - 使用双重检查锁保证多线程环境下的唯一性
        - 支持惰性初始化(首次调用时创建实例)
        - 无初始化参数
    """

    def __init__(cls, name, bases, dct):
        """
        初始化元类相关的单例状态.

        参数:
            cls   : 使用该元类生成的类对象
            name  : 类名字符串
            bases : 基类元组
            dct   : 类体定义的属性字典
        """
        cls._instance = None
        cls._lock = threading.Lock()
        super().__init__(name, bases, dct)

    def __call__(cls):
        """
        控制类的实例化流程, 使其成为单例.

        若实例不存在, 则加锁创建; 否则直接返回已缓存的实例.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__call__()
        return cls._instance

    def instance(cls):
        """
        获取该类的唯一实例(语义化入口).

        等效于直接调用 `MyClass()`, 但可读性更高.
        """
        return cls()
