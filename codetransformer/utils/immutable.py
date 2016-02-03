"""
codetransformer.utils.immutable
-------------------------------

Utilities for creating and working with immutable objects.
"""

from collections import ChainMap
from itertools import starmap
from weakref import WeakKeyDictionary


class immutableattr:
    """An immutable attribute of a class.

    Parameters
    ----------
    attr : any
        The attribute.
    """
    def __init__(self, attr):
        self._attr = attr

    def __get__(self, instance, owner):
        return self._attr


class lazyval:
    """A memoizing property.

    Parameters
    ----------
    func : callable
        The function used to compute the value of the descriptor.
    """
    def __init__(self, func):
        self._cache = WeakKeyDictionary()
        self._func = func

    def __get__(self, instance, owner):
        if instance is None:
            return self

        cache = self._cache
        try:
            return cache[instance]
        except KeyError:
            cache[instance] = val = self._func(instance)
            return val


def _no_arg_init(self):
    pass


object_setattr = object.__setattr__


def initialize_slot(obj, name, value):
    """Initalize an unitialized slot to a value.

    If there is already a value for this slot, this is a nop.

    Parameters
    ----------
    obj : immutable
        An immutable object.
    name : str
        The name of the slot to initialize.
    value : any
        The value to initialize the slot to.
    """
    if not hasattr(obj, name):
        object_setattr(obj, name, value)


def _create_init(slots, defaults):
    """Create the __init__ function for an immutable object.

    Parameters
    ----------
    slots : iterable of str
        The __slots__ field from the class.
    defaults : dict or None
        The default values for the arguments to __init__.

    Returns
    -------
    init : callable
        The __init__ function for the new immutable class.
    """
    if any(s.startswith('__') for s in slots):
        raise TypeError(
            "immutable classes may not have slots that start with '__'",
        )

    # If we have no defaults, ignore all of this.
    kwdefaults = None
    if defaults is not None:
        hit_default = False
        _defaults = []  # positional defaults
        kwdefaults = {}  # kwonly defaults
        kwdefs = False
        for s in slots:
            if s not in defaults and hit_default:
                raise SyntaxError(
                    'non-default argument follows default argument'
                )

            if not kwdefs:
                try:
                    # Try to grab the next default.
                    # Pop so that we know they were all consumed when we
                    # are done.
                    _defaults.append(defaults.pop(s))
                except KeyError:
                    # Not in the dict, we haven't hit any defaults yet.
                    pass
                else:
                    # We are now consuming default arguments.
                    hit_default = True
                if s.startswith('*'):
                    if s in defaults:
                        raise TypeError(
                            'cannot set default for var args or var kwargs',
                        )
                    if not s.startswith('**'):
                        kwdefs = True
            else:
                kwdefaults[s] = defaults.pop(s)

        if defaults:
            # We didn't consume all of the defaults.
            raise TypeError(
                'default value for non-existent argument%s: %s' % (
                    's' if len(defaults) > 1 else '',
                    ', '.join(starmap('{0}={1!r}'.format, defaults.items())),
                )
            )

        # cast back to tuples
        defaults = tuple(_defaults)

    if not slots:
        return _no_arg_init, ()

    ns = {'__initialize_slot': initialize_slot}
    slotnames = tuple(s.strip('*') for s in slots)
    # We are using exec here so that we can later inspect the call signature
    # of the __init__. This makes the positional vs keywords work as intended.
    # This is totally reasonable, no h8 m8!
    exec(
        'def __init__(__self, {args}):    \n    {assign}'.format(
            args=', '.join(slots),
            assign='\n    '.join(
                map('__initialize_slot(__self, "{0}", {0})'.format, slotnames),
            ),
        ),
        ns,
    )
    init = ns['__init__']
    init.__defaults__ = defaults
    init.__kwdefaults__ = kwdefaults
    return init, slotnames


def _wrapinit(init):
    """Wrap an existing initialize function by thawing self for the duration
    of the init.

    Parameters
    ----------
    init : callable
        The user-provided init.

    Returns
    -------
    wrapped : callable
        The wrapped init method.
    """
    def __init__(*args, **kwargs):
        self = args[0]  # they could name this whatever and this breaks kwargs.

        __setattr__._initializing.add(self)
        init(*args, **kwargs)
        __setattr__._initializing.remove(self)

        missing_slots = tuple(
            filter(lambda s: not hasattr(self, s), self.__slots__),
        )
        if missing_slots:
            raise TypeError(
                'not all slots initialized in __init__, missing: {0}'.format(
                    missing_slots,
                ),
            )

    return __init__


def __setattr__(self, name, value):
    if self not in __setattr__._initializing:
        raise AttributeError('cannot mutate immutable object')
    object_setattr(self, name, value)
__setattr__._initializing = set()


def __repr__(self):
    return '{cls}({args})'.format(
        cls=type(self).__name__,
        args=', '.join(starmap(
            '{0}={1!r}'.format,
            ((s, getattr(self, s)) for s in self.__slots__),
        )),
    )


class ImmutableMeta(type):
    """A metaclass for creating immutable objects.
    """
    def __new__(mcls, name, bases, dict_, *, defaults=None):
        if '__slots__' not in dict_:
            raise TypeError('immutable classes must have a __slots__')
        if '__setattr__' in dict_:
            raise TypeError('immutable classes cannot have a __setattr__')

        try:
            dict_['__init__'] = _wrapinit(dict_['__init__'])
        except KeyError:
            dict_['__init__'], dict_['__slots__'] = _create_init(
                dict_['__slots__'], defaults,
            )

        dict_['__setattr__'] = __setattr__
        cls = super().__new__(mcls, name, bases, dict_)

        if cls.__repr__ is object.__repr__:
            # Put a namedtuple-like repr on this class if there is no custom
            # repr on the class.
            cls.__repr__ = __repr__

        return cls

    def __init__(self, *args, defaults=None):
        # ignore the defaults kwarg.
        return super().__init__(*args)


class immutable(metaclass=ImmutableMeta):
    """A base class for immutable objects.
    """
    __slots__ = ()

    def to_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}

    def update(self, **updates):
        return type(self)(**ChainMap(updates, self.to_dict()))
