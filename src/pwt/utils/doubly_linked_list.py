"""
DLinkedList 模块

提供基于哨兵节点的高效双向链表实现.
兼容 Python 序列协议,支持增/删/查/切片/迭代等操作.

主要组件:
- DLinkedNode: 链表节点,包含 data/prev/next 属性
- DLinkedList: 核心链表类,实现插入/删除/索引/切片/迭代等功能

示例:
    >>> dll = DLinkedList([1, 2, 3])
    >>> dll.add_head(0)
    >>> list(dll)
    [0, 1, 2, 3]
    >>> isinstance(dll[1:3], DLinkedList)
    True
"""

from __future__ import annotations

from itertools import islice
from typing import Any, Callable, Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


class DLinkedNode(Generic[T]):
    """
    双向链表节点.

    Attributes:
        data (T): 节点存储的数据.
        prev (DLinkedNode[Any]): 指向前驱节点的引用,初始化时指向自身.
        next (DLinkedNode[Any]): 指向后继节点的引用,初始化时指向自身.
    """

    __slots__ = ("data", "prev", "next")

    def __init__(self, data: T) -> None:
        """
        初始化一个孤立节点
        prev 和 next 均指向自身.

        Args:
            data (T): 节点存储的数据.
        """
        self.data: T = data
        self.prev: DLinkedNode[Any] = self
        self.next: DLinkedNode[Any] = self


class DLinkedList:  # Doubly Linked List (DLinkedList or DLL)
    """
    基于哨兵节点的双向链表实现.

    支持高效的头尾插入和删除操作,并完整兼容 Python 序列协议,
    包括索引访问/切片/迭代/反向迭代等.
    """

    def __init__(self, items: Iterable[Any] | None = None) -> None:
        """
        初始化双向链表.

        Args:
            items (Iterable[Any] | None): 可选的可迭代对象,用于初始化链表元素.
        """
        self._sentinel = DLinkedNode(None)
        self._length = 0

        if items is not None:
            self.extend_tail(items)

    def __getitem__(self, index: int | slice) -> Any | DLinkedList:
        """
        返回指定索引或切片对应的元素或子链表.

        Args:
            index (int | slice): 单个索引或切片对象.

        Returns:
            Any | DLinkedList: 单个元素或子链表.

        Raises:
            IndexError: 索引超出范围.
        """
        if isinstance(index, slice):
            start, stop, step = index.indices(self._length)
            new_slice = DLinkedList()
            for data in islice(self, start, stop, step):
                new_slice.add_tail(data)
            return new_slice
        return self.get_at(index)

    def __setitem__(self, index: int, data: Any) -> None:
        """
        将指定位置的元素替换为新的数据.

        Args:
            index (int): 要设置的元素索引.
            data (Any): 新的数据.

        Raises:
            IndexError: 索引超出范围.
        """
        node = self.get_node_at(index)
        node.data = data

    def __delitem__(self, index: int) -> None:
        """
        删除指定索引位置的元素.

        Args:
            index (int): 要删除的元素索引.

        Raises:
            IndexError: 索引超出范围.
        """
        node = self.get_node_at(index)
        self.remove(node)

    def __eq__(self, other: Any) -> bool:
        """
        判断两个链表是否相等.

        相等条件:同为 DLinkedList,且元素顺序和值完全一致.

        Args:
            other (Any): 待比较对象.

        Returns:
            bool: 相等返回 True,否则 False.
        """
        if not isinstance(other, DLinkedList):
            return False
        if len(self) != len(other):
            return False
        node_self = self._sentinel.next
        node_other = other._sentinel.next
        while node_self is not self._sentinel:
            if node_self.data != node_other.data:
                return False
            node_self = node_self.next
            node_other = node_other.next
        return True

    def __len__(self) -> int:
        """
        返回链表长度.

        Returns:
            int: 元素个数.
        """
        return self._length

    def __contains__(self, data: Any) -> bool:
        """
        判断链表中是否包含指定数据.

        Args:
            data (Any): 待查找的数据.

        Returns:
            bool: 找到返回 True,否则 False.
        """
        node = self._sentinel.next
        while node is not self._sentinel:
            if node.data == data:
                return True
            node = node.next
        return False

    def __iter__(self) -> Iterator[Any]:
        """
        正向迭代链表元素.

        Yields:
            Any: 按顺序返回的每个元素.
        """
        node = self._sentinel.next
        while node is not self._sentinel:
            yield node.data
            node = node.next

    def __reversed__(self) -> Iterator[Any]:
        """
        反向迭代链表元素.

        Yields:
            Any: 按逆序返回的每个元素.
        """
        node = self._sentinel.prev
        while node is not self._sentinel:
            yield node.data
            node = node.prev

    def __repr__(self) -> str:
        """
        返回链表的字符串表示.

        Returns:
            str: 类似 "DLinkedList([a, b, c])" 的格式.
        """
        items = ", ".join(repr(data) for data in self)
        return f"{self.__class__.__name__}([{items}])"

    # ===========================================================================

    def push(self, data: T, first: bool = False) -> DLinkedNode[T]:
        """
        在头部或尾部添加元素.

        Args:
            data (T): 要添加的数据.
            first (bool): True 则在头部添加,False 则在尾部添加.默认为 False.

        Returns:
            DLinkedNode[T]: 新创建的节点.
        """
        if first:
            return self.add_head(data)
        return self.add_tail(data)

    def add_head(self, data: T) -> DLinkedNode[T]:
        """
        在链表头部插入元素.

        Args:
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.
        """
        return self.insert_after(self._sentinel, data)

    def add_tail(self, data: T) -> DLinkedNode[T]:
        """
        在链表尾部插入元素.

        Args:
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.
        """
        return self.insert_before(self._sentinel, data)

    def insert_before(self, node: DLinkedNode[Any], data: T) -> DLinkedNode[T]:
        """
        在指定节点前插入新节点.

        Args:
            node (DLinkedNode[Any]): 参考节点,新节点将插入到该节点之前.
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.
        """
        new_node = DLinkedNode(data)
        new_node.prev = node.prev
        new_node.next = node
        node.prev.next = new_node
        node.prev = new_node
        self._length += 1
        return new_node

    def insert_after(self, node: DLinkedNode[Any], data: T) -> DLinkedNode[T]:
        """
        在指定节点后插入新节点.

        Args:
            node (DLinkedNode[Any]): 参考节点,新节点将插入到该节点之后.
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.
        """
        new_node = DLinkedNode(data)
        new_node.prev = node
        new_node.next = node.next
        node.next.prev = new_node
        node.next = new_node
        self._length += 1
        return new_node

    def insert_before_at(self, index: int, data: T) -> DLinkedNode[T]:
        """
        在指定索引前插入元素.

        Args:
            index (int): 插入位置的索引.
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.

        Raises:
            IndexError: 索引超出范围.
        """
        node = self.get_node_at(index)
        return self.insert_before(node, data)

    def insert_after_at(self, index: int, data: T) -> DLinkedNode[T]:
        """
        在指定索引后插入元素.

        Args:
            index (int): 插入位置的索引.
            data (T): 要添加的数据.

        Returns:
            DLinkedNode[T]: 新创建的节点.

        Raises:
            IndexError: 索引超出范围.
        """
        node = self.get_node_at(index)
        return self.insert_after(node, data)

    def extend_head(self, items: Iterable[T]) -> None:
        """
        在头部依次添加多个元素.

        Args:
            items (Iterable[T]): 包含要添加的数据序列.
        """
        for data in items:
            self.add_head(data)

    def extend_tail(self, items: Iterable[T]) -> None:
        """
        在尾部依次添加多个元素.

        Args:
            items (Iterable[T]): 包含要添加的数据序列.
        """
        for data in items:
            self.add_tail(data)

    # ===========================================================================

    def pop(self, first: bool = False) -> Any:
        """
        从头部或尾部移除并返回一个元素.

        Args:
            first (bool): True 则从头部移除,False 则从尾部移除.默认为 False.

        Returns:
            Any: 被移除的元素.

        Raises:
            IndexError: 链表为空时无法操作.
        """
        if self.is_empty():
            raise IndexError("Cannot access from empty list")
        node = self._sentinel.next if first else self._sentinel.prev
        return self.remove(node)

    def remove_head(self) -> Any:
        """
        移除并返回头部元素.

        Returns:
            Any: 被移除的元素.

        Raises:
            IndexError: 链表为空时无法操作.
        """
        return self.pop(first=True)

    def remove_tail(self) -> Any:
        """
        移除并返回尾部元素.

        Returns:
            Any: 被移除的元素.

        Raises:
            IndexError: 链表为空时无法操作.
        """
        return self.pop(first=False)

    def remove(self, node: DLinkedNode[T]) -> T:
        """
        移除指定节点并返回其数据.

        Args:
            node (DLinkedNode[T]): 要移除的节点.

        Returns:
            T: 被移除节点存储的数据.

        Raises:
            ValueError: 试图移除哨兵节点时抛出.
        """
        if node is self._sentinel:
            raise ValueError("Cannot remove sentinel node")
        node.prev.next = node.next
        node.next.prev = node.prev
        # node.prev = node
        # node.next = node
        del node.prev
        del node.next
        self._length -= 1
        return node.data

    def remove_at(self, index: int) -> Any:
        """
        移除并返回指定索引位置的元素.

        Args:
            index (int): 要移除元素的索引.

        Returns:
            Any: 被移除的元素.

        Raises:
            IndexError: 索引超出范围.
        """
        node = self.get_node_at(index)
        return self.remove(node)

    # ===========================================================================

    def peek(self, first: bool = False) -> Any:
        """
        查看头部或尾部元素但不移除.

        Args:
            first (bool): True 则查看头部,False 则查看尾部.默认为 False.

        Returns:
            Any: 对应位置的元素.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        return self.peek_node(first).data

    def peek_node(self, first: bool = False) -> DLinkedNode[Any]:
        """
        查看头部或尾部节点但不移除.

        Args:
            first (bool): True 则查看头部节点,False 则查看尾部节点.默认为 False.

        Returns:
            DLinkedNode[Any]: 对应位置的节点.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        if self.is_empty():
            raise IndexError("Cannot access from empty list")
        node = self._sentinel.next if first else self._sentinel.prev
        return node

    def get_head(self) -> Any:
        """
        获取头部元素.

        Returns:
            Any: 头部元素的数据.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        return self.get_node_head().data

    def get_node_head(self) -> DLinkedNode[Any]:
        """
        获取头部节点.

        Returns:
            DLinkedNode[Any]: 头部节点.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        return self.peek_node(first=True)

    def get_tail(self) -> Any:
        """
        获取尾部元素.

        Returns:
            Any: 尾部元素的数据.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        return self.get_node_tail().data

    def get_node_tail(self) -> DLinkedNode[Any]:
        """
        获取尾部节点.

        Returns:
            DLinkedNode[Any]: 尾部节点.

        Raises:
            IndexError: 链表为空时无法访问.
        """
        return self.peek_node(first=False)

    def get_at(self, index: int) -> Any:
        """
        获取指定索引位置的元素.

        Args:
            index (int): 元素索引.

        Returns:
            Any: 对应位置的元素.

        Raises:
            IndexError: 索引超出范围.
        """
        return self.get_node_at(index).data

    def get_node_at(self, index: int) -> DLinkedNode[Any]:
        """
        获取指定索引位置的节点.

        Args:
            index (int): 节点索引,可为负数(支持反向索引).

        Returns:
            DLinkedNode[Any]: 对应位置的节点.

        Raises:
            IndexError: 索引超出范围.
        """
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise IndexError("Index out of range")

        if index < self._length / 2:
            node = self._sentinel.next
            for _ in range(index):
                node = node.next
        else:
            node = self._sentinel.prev
            for _ in range(self._length - index - 1):
                node = node.prev
        return node

    # ===========================================================================

    def index_of(self, data: Any) -> int:
        """
        查找指定数据的索引.

        Args:
            data (Any): 要查找的数据.

        Returns:
            int: 数据首次出现的位置.

        Raises:
            ValueError: 数据不在链表中时抛出.
        """
        node = self._sentinel.next
        for index in range(self._length):
            if node.data == data:
                return index
            node = node.next
        raise ValueError("Data not found in list")

    def find(self, predicate: Callable[[T], bool]) -> DLinkedNode[T]:
        """
        根据谓词查找符合条件的第一个节点.

        Args:
            predicate (Callable[[T], bool]): 判定函数,返回 True 则匹配.

        Returns:
            DLinkedNode[T]: 第一个符合条件的节点.

        Raises:
            ValueError: 无任何节点满足谓词时抛出.
        """
        node = self._sentinel.next
        while node is not self._sentinel:
            if predicate(node.data):
                return node
            node = node.next
        raise ValueError("Predicate not found in list")

    # ===========================================================================

    def is_empty(self) -> bool:
        """
        判断链表是否为空.

        Returns:
            bool: 为空返回 True,否则 False.
        """
        return self._length == 0

    def clear(self) -> None:
        """
        清空链表中所有元素,重置长度为 0.
        """
        node = self._sentinel.next
        while node is not self._sentinel:
            next_node = node.next
            # node.prev = self._sentinel
            # node.next = self._sentinel
            del node.prev
            del node.next
            node = next_node
        self._sentinel.next = self._sentinel
        self._sentinel.prev = self._sentinel
        self._length = 0

    def iter_node(self) -> Iterator[DLinkedNode[Any]]:
        """
        正向迭代链表中的所有节点.

        Yields:
            DLinkedNode[Any]: 下一个节点.
        """
        node = self._sentinel.next
        while node is not self._sentinel:
            yield node
            node = node.next

    def iter_node_first(self) -> Iterator[DLinkedNode[Any]]:
        """
        反向迭代链表中的所有节点.

        Yields:
            DLinkedNode[Any]: 下一个节点.
        """
        node = self._sentinel.prev
        while node is not self._sentinel:
            yield node
            node = node.prev
