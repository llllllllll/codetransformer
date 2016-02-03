from codetransformer.instructions import Instruction


def test_repr_types():
    assert repr(Instruction) == 'Instruction'
    for tp in Instruction.__subclasses__():
        assert repr(tp) == tp.opname
