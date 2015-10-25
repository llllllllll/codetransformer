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


def flip(f, a, b):
    """Flips the argument order to f.

    Parameters
    ----------
    f : callable
        The function to call.
    a : any
        The second argument to f.
    b : any
        The first argument to f.

    Returns
    -------
    c : any
        f(b, a)
    """
    return f(b, a)
