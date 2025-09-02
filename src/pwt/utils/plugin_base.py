"""
Python插件系统核心实现

此模块提供了一个可扩展的插件机制基础框架,
涵盖了插件抽象基类的定义/插件异常体系, 以及两种插件加载方式:
  1. from_entry_point, 基于entry points机制
  2. from_dynamic_import, 基于动态导入机制

宿主程序:
  - 定义抽象子类继承`PluginBase`类, 约定 `__init__` 和 `execute` 方法的参数.
  - 调用 `from_entry_point` 或 `from_dynamic_import` 工厂方法初始化插件.
  - 调用插件的 `execute` 方法.

插件程序:
  - 定义一个插件类继承 `PluginBase` 类.
  - 实现 `__init__` 方法, 参数需宿主约定.
  - 实现 `execute` 方法, 参数需宿主约定.
  - 设置 `pyproject.toml` 的 [project.entry-points."约定的组名"] 注册插件. (仅entry points)

用法示例:
```python
# 宿主程序
from plugin_base import PluginBase as _PluginBase

class PluginBase(_PluginBase):
    def __init__(self, arg1, arg2, *, argX="argX") -> None:
        self.arg1 = arg1
        self.arg2 = arg2
        self.argX = argX

    @override
    def execute(self, context) -> Any:
        pass

plugin1 = PluginBase.from_entry_point("plugin1", ["entry.point.name"])
plugin2 = PluginBase.from_dynamic_import("plugin2", ["packname.{plugin_name}.Plugin"])

#插件程序
from plugin_base import PluginBase

class Plugin(PluginBase):
    def __init__(self, arg1, arg2) -> None:
        super().__init__(arg1, arg2)

    @abstractmethod
    @override
    def execute(self, context) -> Any:
        # 插件操作代码
        return context
```

配置示例:
```toml
[project.entry-points."entry.point.name"]
plugin1 = "plugin_base:Plugin"
```
"""

__version__ = "1.1.0"
__author__ = "FB"
__license__ = "MIT License"

import importlib
from abc import ABC, abstractmethod
from importlib.metadata import entry_points
from typing import Any, Iterable, Type, TypeVar


class PluginError(Exception):
    """
    插件异常基类

    作为所有插件相关异常的公共父类, 主要用于异常类型的判断.
    当在插件系统的各个环节出现异常时, 可通过判断是否为该类的实例来处理插件相关异常.
    """

    pass


class PluginNotFoundError(PluginError):
    """
    插件未找到异常

    当遍历全部位置仍然找不到请求的插件时触发.
    """

    def __init__(self, plugin_name: str):
        """
        初始化异常

        Args:
            plugin_name (str): 未找到的插件名称.
        """

        super().__init__(f"Plugin '{plugin_name}' not found")


class PluginInitError(PluginError):
    """
    插件初始化异常

    当插件类实例化过程中发生错误时触发.
    """

    def __init__(self, ex: Exception) -> None:
        """
        初始化异常

        Args:
            ex (Exception): 原始的异常实例.
        """

        super().__init__(f"{type(ex).__name__}: {str(ex)}")


class PluginValueError(PluginError):
    """
    工厂方法参数异常

    当工厂方法接收到无效参数时触发.
    """

    def __init__(self, ex: Exception) -> None:
        """
        初始化异常

        Args:
            ex (Exception): 原始的异常实例.
        """

        super().__init__(f"{type(ex).__name__}: {str(ex)}")


class PluginBase(ABC):
    """
    插件抽象基类

    该类定义了插件的基本结构和行为, 为插件系统提供了统一的接口.
    所有具体的插件类都应该继承自这个基类, 并实现其抽象方法.
    """

    T = TypeVar("T", bound="PluginBase")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        执行插件核心功能

        该方法是插件的核心执行逻辑, 具体的插件需要实现此方法来完成特定的任务.

        Args:
            *args: 位置参数, 用于传递给插件执行时所需的位置参数.
            **kwargs: 关键字参数, 用于传递给插件执行时所需的关键字参数.

        Returns:
            Any: 插件执行结果, 类型由具体实现决定.

        Raises:
            Exception: 当插件执行过程中发生错误时抛出, 插件实现可以根据需要抛出异常.
        """

        pass

    @classmethod
    def from_entry_point(
        cls: Type[T],
        plugin_name: str,
        entry_point_groups: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        通过 entry points 机制加载插件

        遍历指定的 entry point 组, 查找并初始化名称匹配的插件.

        Args:
            plugin_name (str): 目标插件名称, 即要加载的插件的名称.
            entry_point_groups (Iterable[str]): 要搜索的 entry point 组列表.
            *args: 传递给插件构造器的位置参数, 用于初始化插件实例.
            **kwargs: 传递给插件构造器的关键字参数, 用于初始化插件实例.

        Returns:
            T: 实例化的插件对象, 是 `PluginBase` 的子类实例.

        Raises:
            PluginNotFoundError: 无法找到匹配的类..
            PluginInitError: 插件实例化失败.
        """

        for entry_point_group in entry_point_groups:
            for entry_point in entry_points(group=entry_point_group):
                if entry_point.name != plugin_name:
                    continue
                try:
                    plugin_class = entry_point.load()
                except (ImportError, AttributeError):
                    continue
                if not issubclass(plugin_class, cls):
                    continue
                try:
                    return plugin_class(*args, **kwargs)
                except Exception as ex:
                    raise PluginInitError(ex) from ex
        raise PluginNotFoundError(plugin_name)

    @classmethod
    def from_dynamic_import(
        cls: Type[T],
        plugin_name: str,
        class_path_templates: Iterable[str],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        通过动态导入机制加载插件

        根据类路径模板动态查找插件类并实例化.该方法会遍历给定的类路径模板,
        将插件名称替换到模板中的占位符位置, 然后尝试导入相应的模块和类.

        Args:
            plugin_name (str): 目标插件名称, 用于替换类路径模板中的占位符.
            class_path_templates (Iterable[str]): 类路径模板集合,
                应使用 `{plugin_name}` 占位符, 替代 plugin_name 的内容.
                也可以使用 `{}` 占位符, 但只能使用一次.
            *args: 传递给插件构造器的位置参数, 用于初始化插件实例.
            **kwargs: 传递给插件构造器的关键字参数, 用于初始化插件实例.

        Returns:
            T: 实例化的插件对象, 是 `PluginBase` 的子类实例.

        Raises:
            PluginValueError: 类路径模板格式无效.
            PluginNotFoundError: 无法找到匹配的类.
            PluginInitError: 插件实例化失败.
        """

        for class_path_template in class_path_templates:
            try:
                full_path = class_path_template.format(
                    plugin_name, plugin_name=plugin_name, **kwargs
                )
                module_path, class_name = full_path.rsplit(".", 1)
            except (IndexError, KeyError, ValueError) as ex:
                raise PluginValueError(ex) from ex
            try:
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)
            except (ModuleNotFoundError, AttributeError):
                continue
            if not issubclass(plugin_class, cls):
                continue
            try:
                return plugin_class(*args, **kwargs)
            except Exception as ex:
                raise PluginInitError(ex) from ex
        raise PluginNotFoundError(plugin_name)
