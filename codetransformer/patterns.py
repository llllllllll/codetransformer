from operator import methodcaller
from types import MethodType

from .utils.immutable import immutable


class matchable:
    """Mixin for defining the operators on patterns.
    """
    def __or__(self, other):
        if self is other:
            return self

        if not isinstance(other, matchable):
            return NotImplemented

        patterns = []
        if isinstance(self, or_):
            patterns.extend(self.patterns)
        else:
            patterns.append(self)
        if isinstance(other, or_):
            patterns.extend(other.patterns)
        else:
            patterns.append(other)

        return or_(*patterns)


class seq(immutable, matchable):
    """A sequence of matchables to match in order.

    Parameters
    ----------
    *matchables : iterable of matchable
        The matchables to match against.
    """
    __slots__ = '*matchables',

    def match(self, instrs):
        matched = []
        extend_matched = matched.extend
        for p in self.matchables:
            submatched = p.match(instrs)
            if submatched is None:
                return None
            extend_matched(submatched)
            instrs = instrs[len(submatched):]

        if matched:
            return tuple(matched)

        return None


class or_(immutable, matchable):
    """Binary or of multiple matchables.

    Parameters
    ----------
    *matchables : iterable of matchable
        The matchables to or together.
    """
    __slots__ = '*matchables',

    def match(self, instrs):
        for p in self.matchables:
            matched = p.match(instrs)
            if matched is not None:
                return matched
        return None


class pattern(immutable, defaults={'startcode': (0,)}):
    """A pattern of instructions that can be matched against.

    Parameters
    ----------
    *matchables : iterable of matchable
        The type of instructions to match against.
    startcode : container of any
        The startcodes where this pattern should be tried.
    """
    __slots__ = 'matchable', 'startcode'

    def __new__(cls, *matchables, startcode=(0,)):
        if not matchables:
            raise TypeError('expected at least one matchable')

        self = super().__new__(cls)
        self.__init__(
            seq(*matchables) if len(matchables) > 1 else matchables[0],
            startcode,
        )
        return self

    def __call__(self, f):
        return boundpattern(self.matchable, self.startcode, f)


class boundpattern(immutable):
    """A pattern bound to a function.
    """
    __slots__ = '_matchable', '_startcodes', '_f'

    def __get__(self, instance, owner):
        return type(self)(
            self._matchable,
            self._startcodes,
            MethodType(self._f, instance)
        )

    def __call__(self, instrs, startcode):
        matched_instrs = (
            startcode in self._startcodes and self._matchable.match(instrs)
        )
        if not matched_instrs:
            raise KeyError(instrs, startcode)

        return self._f(*matched_instrs), matched_instrs


class patterndispatcher(immutable):
    """A set of boundpatterns that can dispatch onto instrs.
    """
    __slots__ = '*_boundpatterns',

    def __get__(self, instance, owner):
        return type(self)(*map(
            methodcaller('__get__', instance, owner),
            self._boundpatterns,
        ))

    def __call__(self, instrs, startcode):
        for p in self._boundpatterns:
            try:
                return p(instrs, startcode)
            except KeyError:
                pass

        raise KeyError(instrs, startcode)
