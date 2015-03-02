from types import FunctionType


def with_code_transformation(transformer):
    """
    Decorator that applies a code transformation to a function.

    WARNING: Cannot be used as a class decorator.
    """
    def decorator(f):
        return FunctionType(
            transformer.visit(f.__code__),
            f.__globals__,
            f.__name__,
            f.__defaults__,
            f.__closure__,
        )
    return decorator
