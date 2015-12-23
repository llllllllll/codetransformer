from collections import deque
from itertools import islice
from toolz import complement, flip


def is_a(type_):
    """More curryable version of isinstance."""
    return flip(isinstance, type_)


def not_a(type_):
    """More curryable version of not isinstance."""
    return complement(is_a(type_))


def scanl(f, n, ns):
    """Reduce ns by f starting with n yielding each intermediate value.

    tuple(scanl(f, n, ns))[-1] == reduce(f, ns, n)

    Parameters
    ----------
    f : callable
        A binary function.
    n : any
        The starting value.
    ns : iterable of any
        The iterable to scan over.

    Yields
    ------
    p : any
        The value of reduce(f, ns[:idx]) where idx is the current index.

    Examples
    --------
    >>> import operator as op
    >>> tuple(scanl(op.add, 0, (1, 2, 3, 4)))
    (0, 1, 3, 6, 10)
    """
    yield n
    for m in ns:
        n = f(n, m)
        yield n


def reverse_dict(d):
    """Reverse a dictionary, replacing the keys and values.

    Parameters
    ----------
    d : dict
        The dict to reverse.

    Returns
    -------
    rd : dict
        The dict with the keys and values flipped.

    Examples
    --------
    >>> d = {'a': 1, 'b': 2, 'c': 3}
    >>> e = reverse_dict(d)
    >>> e == {1: 'a', 2: 'b', 3: 'c'}
    True
    """
    return {v: k for k, v in d.items()}


def ffill(iterable):
    """Forward fill non None values in some iterable.

    Parameters
    ----------
    iterable : iterable
        The iterable to forward fill.

    Yields
    ------
    e : any
        The last non None value or None if there has not been a non None value.
    """
    it = iter(iterable)
    previous = next(it)
    yield previous
    for e in it:
        if e is None:
            yield previous
        else:
            previous = e
            yield e


def moving_window(n, iterable):
    """
    Generate n-tuples of elements yielded by ``iterator``.

    Example
    -------
    >>> list(moving_window(2, range(5)))
    [(0, 1), (1, 2), (2, 3), (3, 4)]
    """
    iterator = iter(iterable)
    to_yield = deque(islice(iterator, n))
    if len(to_yield) < n:
        raise ValueError("Iterator only yielded %d elements." % len(to_yield))

    yield tuple(to_yield)
    while True:
        to_yield.popleft()
        to_yield.append(next(iterator))
        yield tuple(to_yield)
