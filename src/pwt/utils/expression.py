from __future__ import annotations

import re
from typing import Any, overload

import rule_engine


class ExpressionError(Exception):
    def __init__(self, original: Exception):
        self.original = original
        if isinstance(original, rule_engine.EngineError):
            super().__init__(repr(self.original))
        else:
            super().__init__(self.original.args)


class ExprFlag:
    """表达式标志位占位类型(预留, 暂未使用)"""

    pass


class Expression:
    """
    表达式封装类, 当前基于 rule_engine 实现.
    - evaluate: 返回表达式计算结果, 可选 default 兜底
    - match: 返回布尔判定结果, 可选 default 兜底
    - variables: 返回表达式中引用的变量名(简易实现)
    """

    def __init__(
        self,
        expr: str,
        *flags: ExprFlag,
    ) -> None:
        self.expr = expr
        self.flags = flags
        self._rule = rule_engine.Rule(
            self.expr,
            rule_engine.Context(resolver=self._resolver),
        )

    @overload
    def evaluate(self, /, *, default: Any = ..., **kwds: Any) -> Any: ...
    @overload
    def evaluate(self, data: Any, /, *, default: Any = ...) -> Any: ...
    def evaluate(self, data: Any = ..., /, *, default: Any = ..., **kwds: Any) -> Any:
        """
        计算表达式的值.
        :param data: 上下文数据
        :param default: 当计算失败时返回的默认值; 未传则抛异常
        """
        if data is ...:
            data = kwds
        try:
            return self._rule.evaluate(data)
        except Exception as ex:
            if default is ...:
                if isinstance(ex, rule_engine.EngineError):
                    raise ExpressionError(ex)
                raise
            return default

    @overload
    def match(self, /, *, default: Any = ..., **kwds: Any) -> Any: ...
    @overload
    def match(self, data: Any, /, *, default: Any = ...) -> Any: ...
    def match(self, data: Any = ..., /, *, default: Any = ..., **kwds: Any) -> bool:
        """
        判断表达式是否匹配(布尔结果).
        :param data: 上下文数据
        :param default: 当计算失败时返回的默认值; 未传则抛异常
        """
        return bool(self.evaluate(data, default=default, **kwds))

    def variables(self) -> set[str]:
        """
        返回表达式中引用的变量名.
        当前为简易正则实现, 未来可替换为 AST 解析以提高准确性.
        """
        tokens = re.findall(r"[A-Za-z_]\w*", self.expr)
        keywords = {"and", "or", "not", "True", "False", "None"}
        return {t for t in tokens if t not in keywords}

    def _resolver(self, data: Any, name: str) -> Any:
        try:
            return rule_engine.resolve_item(data, name)
        except Exception:
            return rule_engine.resolve_attribute(data, name)


def compile(
    expr: str,
    *flags: ExprFlag,
) -> Expression:
    return Expression(expr, *flags)


def evaluate(
    expr: str,
    data: Any,
    *flags: ExprFlag,
    default: Any = ...,
) -> Any:
    return compile(expr, *flags).evaluate(data, default=default)


def match(
    expr: str,
    data: Any,
    *flags: ExprFlag,
    default: Any = ...,
) -> bool:
    return compile(expr, *flags).match(data, default=default)


# from typing import Any, Iterable, Mapping

# from lark import Lark, Token, Transformer

# _GRAMMAR = r"""
#     ?start: comparison
#     ?comparison: calculation "==" calculation    -> equal
#                | calculation "!=" calculation    -> not_equal
#                | calculation "<=" calculation    -> subset
#                | calculation ">=" calculation    -> superset
#                | calculation "<"  calculation    -> proper_subset
#                | calculation ">"  calculation    -> proper_superset
#     ?calculation: factor
#                 | calculation "&" factor    -> intersection
#                 | calculation "|" factor    -> union
#                 | calculation "-" factor    -> difference
#                 | calculation "^" factor    -> symmetric_difference
#     ?factor: literal | "(" calculation ")"
#     ?literal: EMPTY | VARIABLE
#     EMPTY: "empty"
#     VARIABLE: /[A-Za-z0-9_]{1,31}/
#     %import common.WS
#     %ignore WS
# """

# _lark = Lark(_GRAMMAR, parser="lalr")


# class _EvalTransformer(Transformer[Token, bool]):
#     """
#     用于评估和转换语法树的类
#     """

#     def __init__(self, variables: Mapping[str, Iterable[Any]]) -> None:
#         super().__init__()
#         self._variables = variables

#     def VARIABLE(self, token: Token):
#         return set(self._variables.get(token, set()))

#     def EMPTY(self, _):
#         return set()

#     def equal(self, nodes: list[set]):  # 相等
#         return nodes[0] == nodes[1]

#     def not_equal(self, nodes: list[set]):  # 不相等
#         return nodes[0] != nodes[1]

#     def subset(self, nodes: list[set]):  # 子集
#         return nodes[0] <= nodes[1]

#     def superset(self, nodes: list[set]):  # 超集
#         return nodes[0] >= nodes[1]

#     def proper_subset(self, nodes: list[set]):  # 真子集
#         return nodes[0] < nodes[1]

#     def proper_superset(self, nodes: list[set]):  # 真超集
#         return nodes[0] > nodes[1]

#     def intersection(self, nodes: list[set]):  # 交集
#         return nodes[0] & nodes[1]

#     def union(self, nodes: list[set]):  # 并集
#         return nodes[0] | nodes[1]

#     def difference(self, nodes: list[set]):  # 差集
#         return nodes[0] - nodes[1]

#     def symmetric_difference(self, nodes: list[set]):  # 对称差集
#         return nodes[0] ^ nodes[1]


# class Expression:
#     """
#     一个用于比较和评估表达式的类
#     """

#     def __init__(self, expression: str):
#         """
#         初始化方法

#         Args:
#             expression: 要评估的表达式
#         Raises:
#             UnexpectedInput:
#                 表达式解析错误时, 将出现以下子异常之一:
#                 UnexpectedCharacters, UnexpectedToken, UnexpectedEOF
#         """

#         self.expression = expression
#         self._parse_tree = _lark.parse(self.expression)

#     @property
#     def variables(self) -> set[str]:
#         """表达式中的所有变量名称集合"""
#         return {
#             token.value
#             for token in self._parse_tree.scan_values(
#                 lambda t: isinstance(t, Token) and t.type == "VARIABLE"
#             )
#         }

#     def evaluate(self, variables: Mapping[str, Iterable[Any]]) -> bool:
#         """
#         使用给定的字面量评估表达式

#         Args:
#             variables: 一个字面量字符串对应可迭代对象的字典
#                 每个可迭代对象代表一个字面量的值, 默认为空集合.
#         Returns:
#             表达式的评估结果, `True`表示表达式为真, `False`表示表达式为假.
#         """

#         transformer = _EvalTransformer(variables)
#         return transformer.transform(self._parse_tree)

#     def __repr__(self) -> str:
#         return f"Expression(expression='{self.expression}')"


# 使用 `变量名: 类型` 进行类型转换
# ---

# ## 1. 算术运算符

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `+` | 加法 | `add` |
# | `-` | 减法/取负 | `sub` / `negate` |
# | `*` | 乘法 | `mul` |
# | `/` | 除法 | `div` |
# | `%` | 取余 | `mod` |
# | `**` / `^` | 幂运算 | `pow` |
# | `//` | 整除(Python 风格) | `floordiv` |

# ---

# ## 2. 比较运算符

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `==` | 等于 | `eq` |
# | `!=` / `<>` | 不等于 | `ne` |
# | `>` | 大于 | `gt` |
# | `<` | 小于 | `lt` |
# | `>=` | 大于等于 | `ge` |
# | `<=` | 小于等于 | `le` |
# | `~= ` | 模糊匹配(nginx/Lua) | `match_approx` |
# | `===` | 全等(类型和值都相等, JS) | `strict_eq` |
# | `!==` | 全不等(JS) | `strict_ne` |

# ---

# ## 3. 逻辑运算符

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `&&` / `and` | 逻辑与 | `and_` |
# | `\|\|` / `or` | 逻辑或 | `or_` |
# | `!` / `not` | 逻辑非 | `not_` |
# | `xor` / `^^` | 异或 | `xor` |

# ---

# ## 4. 位运算符

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `&` | 位与 | `bit_and` |
# | `\|` | 位或 | `bit_or` |
# | `^` | 位异或 | `bit_xor` |
# | `~` | 位取反 | `bit_not` |
# | `<<` | 左移 | `shift_left` |
# | `>>` | 右移 | `shift_right` |
# | `>>>` | 无符号右移(JS) | `shift_right_unsigned` |

# ---

# ## 5. 集合/包含测试

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `in` | 属于(集合/区间) | `in_` |
# | `not in` | 不属于 | `not_in` |
# | `⊂` / `subset` | 真子集 | `subset` |
# | `⊆` | 子集等于 | `subset_eq` |
# | `∈` | 集合包含(数学符号) | `member_of` |

# ---

# ## 6. 模式匹配与正则

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `=~` | 正则匹配(Perl/Ruby) | `regex_match` |
# | `!~` | 正则不匹配 | `regex_not_match` |
# | `like` | SQL 模糊匹配 | `like` |
# | `ilike` | SQL 不区分大小写匹配 | `ilike` |

# ---

# ## 7. 其他常见运算符 / 特殊符号

# | 符号 | 含义 | 推荐函数名 |
# |---|---|---|
# | `..` | 区间(Lua/Swift) | `range` |
# | `...` | 闭区间/展开(Rust/JS) | `range_inclusive` / `spread` |
# | `??` | 空值合并(C# / JS) | `null_coalesce` |
# | `?:` | 三元条件(Elvis 运算符/Kotlin) | `ternary` / `elvis` |
# | `=>` | 映射/箭头 | `map_to` |
# | `<=>` | 太空船(比较返回 -1/0/1, Ruby/PHP) | `spaceship` |
# | `::` | 域/作用域解析 | `scope_resolve` |

# ---

# 💡 **设计建议**
# - 如果你打算做跨语言 DSL, 可以为每个符号统一成**数学风格 + 常见程序风格**的二重别名, 比如 `⊂` 和 `subset` 都映射到同一逻辑函数.
# - 函数名建议全小写+下划线, 避免与语言关键字冲突, 比如 `or` → `or_`.
# - 可以维护一个符号到函数名的字典, 用于快速解析和调用对应逻辑.
