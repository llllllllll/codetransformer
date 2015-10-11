from io import StringIO
from textwrap import dedent
from types import CodeType

from ..pretty import a, walk_code


def test_a(capsys):
    text = dedent(
        """
        def inc(a):
            b = a + 1
            return b
        """
    )
    expected = dedent(
        """\
        Module(
          body=[
            FunctionDef(
              name='inc',
              args=arguments(
                args=[
                  arg(
                    arg='a',
                    annotation=None,
                  ),
                ],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
              ),
              body=[
                Assign(
                  targets=[
                    Name(id='b', ctx=Store()),
                  ],
                  value=BinOp(
                    left=Name(id='a', ctx=Load()),
                    op=Add(),
                    right=Num(1),
                  ),
                ),
                Return(
                  value=Name(id='b', ctx=Load()),
                ),
              ],
              decorator_list=[],
              returns=None,
            ),
          ],
        )
        """
    )

    a(text)
    stdout, stderr = capsys.readouterr()
    assert stdout == expected
    assert stderr == ''

    file_ = StringIO()
    a(text, file=file_)
    assert capsys.readouterr() == ('', '')

    result = file_.getvalue()
    assert result == expected


def test_walk_code():
    module = dedent(
        """\
        class Foo:
            def bar(self):
                def buzz():
                    pass
                def bazz():
                    pass
                return buzz
        """
    )

    co = compile(module, '<test>', 'exec')

    foo = [c for c in co.co_consts if isinstance(c, CodeType)][0]
    bar = [c for c in foo.co_consts if isinstance(c, CodeType)][0]
    buzz = [c for c in bar.co_consts
            if isinstance(c, CodeType) and c.co_name == 'buzz'][0]
    bazz = [c for c in bar.co_consts
            if isinstance(c, CodeType) and c.co_name == 'bazz'][0]

    result = list(walk_code(co))
    expected = [
        ('<module>', co),
        ('<module>.Foo', foo),
        ('<module>.Foo.bar', bar),
        ('<module>.Foo.bar.<locals>.buzz', buzz),
        ('<module>.Foo.bar.<locals>.bazz', bazz),
    ]

    assert result == expected
