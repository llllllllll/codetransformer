import sys
import types
from toolz import mapcat

from . import instructions as instrs
from .code import Code


Label = instrs.Label


def assemble_function(signature, objs, code_kwargs=None, function_kwargs=None):
    """TODO
    """
    if code_kwargs is None:
        code_kwargs = {}
    if function_kwargs is None:
        function_kwargs = {}

    code_kwargs.setdefault('argnames', list(gen_argnames_for_code(signature)))

    # Default to using the globals of the calling stack frame.
    function_kwargs.setdefault('globals', sys._getframe(1).f_globals)

    function_kwargs.setdefault('argdefs', tuple(extract_defaults(signature)))

    code = assemble_code(objs, **code_kwargs).to_pycode()

    return types.FunctionType(code, **function_kwargs)


def assemble_code(objs, **code_kwargs):
    """TODO
    """
    instrs = resolve_labels(assemble_instructions(objs))
    return Code(instrs, **code_kwargs)


def assemble_instructions(objs):
    """Assemble a sequence of Instructions or iterables of instructions.
    """
    return list(mapcat(_validate_instructions, objs))


def resolve_labels(objs):
    """TODO
    """
    out = []
    last_instr = None
    for i in reversed(objs):
        if isinstance(i, Label):
            if last_instr is None:
                # TODO: Better error here.
                raise ValueError("Can't end with a Label!")
            # Make any jumps to `i` resolve to `last_instr`.
            last_instr.steal(i)
        elif isinstance(i, instrs.Instruction):
            last_instr = i
            out.append(i)
        else:
            raise TypeError("Unknown type: {}", i)

    for i in out:
        if isinstance(i.arg, Label):
            raise ValueError("Unresolved label for {}".format(i))

    return reversed(out)


def _validate_instructions(obj):
    """TODO
    """
    Instruction = instrs.Instruction
    if isinstance(obj, (Label, Instruction)):
        yield obj
    else:
        for instr in obj:
            if not isinstance(instr, (Instruction, Label)):
                raise TypeError(
                    "Expected an Instruction or Label. Got %s" % obj,
                )
            yield instr


def gen_argnames_for_code(sig):
    """Get argnames from an inspect.signature to pass to a Code object.  """
    for name, param in sig.parameters.items():
        if param.kind == param.VAR_POSITIONAL:
            yield '*' + name
        elif param.kind == param.VAR_KEYWORD:
            yield '**' + name
        else:
            yield name


def extract_defaults(sig):
    """Get default parameters from an inspect.signature.
    """
    return (p.default for p in sig.parameters.values() if p.default != p.empty)
