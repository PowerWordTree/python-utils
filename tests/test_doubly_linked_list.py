"""
双向链表(DLinkedList)测试套件

全面测试DLinkedList类的所有功能,包括边界情况和异常处理.
"""

import pytest

from pwt.utils.doubly_linked_list import DLinkedList


@pytest.fixture
def empty_list():
    """创建一个空的双向链表"""
    return DLinkedList()


@pytest.fixture
def filled_list():
    """创建一个包含元素的双向链表"""
    return DLinkedList([1, 2, 3, 4, 5])


class TestDLinkedListInitialization:
    """测试链表初始化功能"""

    def test_empty_initialization(self, empty_list):
        assert len(empty_list) == 0
        assert list(empty_list) == []
        assert empty_list.is_empty()

    def test_initialization_with_items(self, filled_list):
        assert len(filled_list) == 5
        assert list(filled_list) == [1, 2, 3, 4, 5]
        assert not filled_list.is_empty()

    def test_initialization_with_different_data_types(self):
        dll = DLinkedList(["a", 1, True, None, {"key": "value"}])
        assert len(dll) == 5


class TestDLinkedListBasicOperations:
    """测试链表基本操作"""

    def test_add_head(self, empty_list):
        empty_list.add_head(1)
        empty_list.add_head(2)
        assert list(empty_list) == [2, 1]

    def test_add_tail(self, empty_list):
        empty_list.add_tail(1)
        empty_list.add_tail(2)
        assert list(empty_list) == [1, 2]

    def test_remove_head(self, filled_list):
        assert filled_list.remove_head() == 1
        assert list(filled_list) == [2, 3, 4, 5]

    def test_remove_tail(self, filled_list):
        assert filled_list.remove_tail() == 5
        assert list(filled_list) == [1, 2, 3, 4]

    def test_pop(self, filled_list):
        # 默认从尾部弹出
        assert filled_list.pop() == 5
        # 从头部弹出
        assert filled_list.pop(first=True) == 1
        assert list(filled_list) == [2, 3, 4]

    def test_peek(self, filled_list):
        # 默认查看尾部
        assert filled_list.peek() == 5
        # 查看头部
        assert filled_list.peek(first=True) == 1
        # 不修改链表
        assert len(filled_list) == 5


class TestDLinkedListIndexOperations:
    """测试链表索引操作"""

    def test_get_at(self, filled_list):
        assert filled_list.get_at(0) == 1
        assert filled_list.get_at(2) == 3
        assert filled_list.get_at(-1) == 5

    def test_set_at(self, filled_list):
        filled_list[0] = 10
        filled_list[2] = 30
        filled_list[-1] = 50
        assert list(filled_list) == [10, 2, 30, 4, 50]

    def test_insert_before_at(self, filled_list):
        filled_list.insert_before_at(2, 25)
        assert list(filled_list) == [1, 2, 25, 3, 4, 5]

    def test_insert_after_at(self, filled_list):
        filled_list.insert_after_at(2, 35)
        assert list(filled_list) == [1, 2, 3, 35, 4, 5]

    def test_remove_at(self, filled_list):
        assert filled_list.remove_at(2) == 3
        assert list(filled_list) == [1, 2, 4, 5]

    def test_index_error(self, filled_list):
        with pytest.raises(IndexError):
            filled_list.get_at(10)
        with pytest.raises(IndexError):
            filled_list.get_at(-10)


class TestDLinkedListSlicing:
    """测试链表切片操作"""

    def test_slice_basic(self, filled_list):
        sliced = filled_list[1:4]
        assert isinstance(sliced, DLinkedList)
        assert list(sliced) == [2, 3, 4]

    def test_slice_step(self, filled_list):
        sliced = filled_list[::2]
        assert list(sliced) == [1, 3, 5]

    def test_slice_negative_indices(self, filled_list):
        sliced = filled_list[-3:-1]
        assert list(sliced) == [3, 4]


class TestDLinkedListIteration:
    """测试链表迭代功能"""

    def test_forward_iteration(self, filled_list):
        items = []
        for item in filled_list:
            items.append(item)
        assert items == [1, 2, 3, 4, 5]

    def test_reverse_iteration(self, filled_list):
        items = []
        for item in reversed(filled_list):
            items.append(item)
        assert items == [5, 4, 3, 2, 1]


class TestDLinkedListContains:
    """测试链表包含判断"""

    def test_contains_existing(self, filled_list):
        assert 3 in filled_list
        assert 1 in filled_list
        assert 5 in filled_list

    def test_contains_not_existing(self, filled_list):
        assert 10 not in filled_list
        assert "a" not in filled_list


class TestDLinkedListFindOperations:
    """测试链表查找功能"""

    def test_index_of(self, filled_list):
        assert filled_list.index_of(3) == 2
        assert filled_list.index_of(1) == 0
        assert filled_list.index_of(5) == 4

    def test_index_of_not_found(self, filled_list):
        with pytest.raises(ValueError):
            filled_list.index_of(10)

    def test_find(self, filled_list):
        node = filled_list.find(lambda x: x > 3)
        assert node.data == 4

        node = filled_list.find(lambda x: x % 2 == 0)
        assert node.data == 2

    def test_find_not_found(self, filled_list):
        with pytest.raises(ValueError):
            filled_list.find(lambda x: x > 10)


class TestDLinkedListEdgeCases:
    """测试链表边界情况"""

    def test_empty_operations(self, empty_list):
        with pytest.raises(IndexError):
            empty_list.pop()
        with pytest.raises(IndexError):
            empty_list.peek()
        with pytest.raises(IndexError):
            empty_list.remove_head()
        with pytest.raises(IndexError):
            empty_list.remove_tail()

    def test_clear(self, filled_list):
        filled_list.clear()
        assert len(filled_list) == 0
        assert filled_list.is_empty()
        assert list(filled_list) == []

    def test_extend(self, empty_list):
        empty_list.extend_tail([1, 2, 3])
        assert list(empty_list) == [1, 2, 3]

        empty_list.extend_head([4, 5])
        assert list(empty_list) == [5, 4, 1, 2, 3]


class TestDLinkedListSpecialMethods:
    """测试链表特殊方法"""

    def test_equality(self):
        list1 = DLinkedList([1, 2, 3])
        list2 = DLinkedList([1, 2, 3])
        list3 = DLinkedList([1, 2, 4])

        assert list1 == list2
        assert list1 != list3
        assert list1 != [1, 2, 3]  # 与普通列表不相等

    def test_repr(self, filled_list):
        assert repr(filled_list) == "DLinkedList([1, 2, 3, 4, 5])"

    def test_length(self, filled_list, empty_list):
        assert len(filled_list) == 5
        assert len(empty_list) == 0

        filled_list.add_head(0)
        filled_list.add_tail(6)
        assert len(filled_list) == 7
