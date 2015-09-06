def instance(cls):
    """Decorator for creating one of instances.

    Parameters
    ----------
    cls : type
        A class.

    Returns
    -------
    instance : cls
        A new instance of ``cls``.
    """
    return cls()
