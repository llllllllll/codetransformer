@object.__new__
class no_default:
    def __new__(cls):
        return no_default

    def __repr__(self):
        return 'no_default'
    __str__ = __repr__

    def __reduce__(self):
        return 'no_default'

    def __deepcopy__(self):
        return self
    __copy__ = __deepcopy__
