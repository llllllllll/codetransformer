import pytest

from functools import total_ordering
from inspect import signature

from .. import instructions as instrs
from ..assembler import assemble_function
from ..macros import AssertFail, IfStatement, ForLoop
from ..utils.instance import instance


def assert_same_result(f1, f2, *args, **kwargs):
    try:
        result1 = f1(*args, **kwargs)
        f1_raised = False
    except Exception as e:
        result1 = e
        f1_raised = True

    try:
        result2 = f2(*args, **kwargs)
        f2_raised = False
    except Exception as e:
        result2 = e
        f2_raised = True

    if f1_raised and not f2_raised:
        raise AssertionError("\n{} raised {}\n{} returned {}".format(
            f1.__name__, result1, f2.__name__, result2
        ))
    elif not f1_raised and f2_raised:
        raise AssertionError("\n{} returned {}\n {} raised {}".format(
            f1.__name__, result1, f2.__name__, result2
        ))
    elif f1_raised and f2_raised:
        assert type(result1) == type(result2) and result1.args == result2.args
    else:
        assert result1 == result2


def test_simple_if_statement():

    def goal(x, y):
        z = 0
        if x > y:
            z = 1
        z = z + 1
        return z

    assembly = [
        instrs.LOAD_CONST(0),
        instrs.STORE_FAST('z'),
        IfStatement(
            test=[
                instrs.LOAD_FAST('x'),
                instrs.LOAD_FAST('y'),
                instrs.COMPARE_OP.GT,
            ],
            body=[
                instrs.LOAD_CONST(1),
                instrs.STORE_FAST('z'),
            ],
        ),
        instrs.LOAD_FAST('z'),
        instrs.LOAD_CONST(1),
        instrs.BINARY_ADD(),
        instrs.STORE_FAST('z'),
        instrs.LOAD_FAST('z'),
        instrs.RETURN_VALUE(),
    ]
    func = assemble_function(signature(goal), assembly)

    assert_same_result(func, goal, 1, 1)
    assert_same_result(func, goal, 1, 2)
    assert_same_result(func, goal, 2, 1)
    assert_same_result(func, goal, incomparable, 1)
    assert_same_result(func, goal, 1, incomparable)


def test_if_else():

    def goal(x):
        if x > 0:
            return x
        else:
            return -x

    assembly = [
        IfStatement(
            test=[
                instrs.LOAD_FAST('x'),
                instrs.LOAD_CONST(0),
                instrs.COMPARE_OP.GT,
            ],
            body=[
                instrs.LOAD_FAST('x'),
                instrs.RETURN_VALUE(),
            ],
            else_body=[
                instrs.LOAD_FAST('x'),
                instrs.UNARY_NEGATIVE(),
                instrs.RETURN_VALUE(),
            ],
        ),
        AssertFail("Shouldn't ever get here!"),
    ]

    func = assemble_function(signature(goal), assembly)

    assert_same_result(func, goal, 1)
    assert_same_result(func, goal, 0)
    assert_same_result(func, goal, -1)
    assert_same_result(func, goal, object())


def test_simple_for_loop():

    def goal(x):
        result = []
        for i in range(x):
            result.append(i * 2)
        return result

    assembly = [
        instrs.BUILD_LIST(0),
        instrs.STORE_FAST('result'),
        ForLoop(
            init=[
                instrs.LOAD_GLOBAL('range'),
                instrs.LOAD_FAST('x'),
                instrs.CALL_FUNCTION(1),
            ],
            unpack=[
                instrs.STORE_FAST('i'),
            ],
            body=[
                instrs.LOAD_FAST('result'),
                instrs.LOAD_ATTR('append'),
                instrs.LOAD_FAST('i'),
                instrs.LOAD_CONST(2),
                instrs.BINARY_MULTIPLY(),
                instrs.CALL_FUNCTION(1),
                instrs.POP_TOP(),
            ],
        ),
        instrs.LOAD_FAST('result'),
        instrs.RETURN_VALUE(),
    ]

    func = assemble_function(signature(goal), assembly)

    assert_same_result(func, goal, 1)
    assert_same_result(func, goal, 2)
    assert_same_result(func, goal, 3)
    assert_same_result(func, goal, -1)
    assert_same_result(func, goal, "this should crash")


def test_nested_for_loop():

    def goal(x, y):
        result = []
        for i in range(x):
            for j in range(y):
                result.append(i + j)
        return result

    assembly = [
        instrs.BUILD_LIST(0),
        instrs.STORE_FAST('result'),
        ForLoop(
            init=[
                instrs.LOAD_GLOBAL('range'),
                instrs.LOAD_FAST('x'),
                instrs.CALL_FUNCTION(1),
            ],
            unpack=[
                instrs.STORE_FAST('i'),
            ],
            body=[
                ForLoop(
                    init=[
                        instrs.LOAD_GLOBAL('range'),
                        instrs.LOAD_FAST('y'),
                        instrs.CALL_FUNCTION(1),
                    ],
                    unpack=[
                        instrs.STORE_FAST('j'),
                    ],
                    body=[
                        instrs.LOAD_FAST('result'),
                        instrs.LOAD_ATTR('append'),
                        instrs.LOAD_FAST('i'),
                        instrs.LOAD_FAST('j'),
                        instrs.BINARY_ADD(),
                        instrs.CALL_FUNCTION(1),
                        instrs.POP_TOP(),
                    ],
                ),
            ],
        ),
        instrs.LOAD_FAST('result'),
        instrs.RETURN_VALUE(),
    ]

    func = assemble_function(signature(goal), assembly)

    assert_same_result(func, goal, 0, 0)
    assert_same_result(func, goal, 5, 3)
    assert_same_result(func, goal, 3, 5)
    assert_same_result(func, goal, -1, -1)
    assert_same_result(func, goal, "this should", "crash")


def test_for_else():

    def goal(x):
        for obj in ('a', 'b', 'c'):
            if x == obj:
                return 'found'
        else:
            return 'not found'

    assembly = [
        ForLoop(
            init=[instrs.LOAD_CONST(('a', 'b', 'c'))],
            unpack=[instrs.STORE_FAST('obj')],
            body=[
                IfStatement(
                    test=[
                        instrs.LOAD_FAST('x'),
                        instrs.LOAD_FAST('obj'),
                        instrs.COMPARE_OP.EQ,
                    ],
                    body=[instrs.LOAD_CONST('found'), instrs.RETURN_VALUE()],
                )
            ],
            else_body=[instrs.LOAD_CONST('not found'), instrs.RETURN_VALUE()],
        ),
        AssertFail("Shouldn't ever get here!"),
    ]

    func = assemble_function(signature(goal), assembly)

    assert_same_result(func, goal, 'a')
    assert_same_result(func, goal, 'b')
    assert_same_result(func, goal, 'not in the tuple')


def test_assert_fail():
    assembly = [AssertFail('message')]
    func = assemble_function(signature(lambda: None), assembly)

    with pytest.raises(AssertionError) as e:
        func()

    assert e.value.args == ('message',)


@instance
@total_ordering
class incomparable:
    def __lt__(self, other):
        raise TypeError("Nothing compares to me!")
