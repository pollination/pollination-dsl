from pollination_dsl.dag.inputs import IntegerInput


def test_local_default():
    inp = IntegerInput(
        default=10,
        default_local=20
    )
    inp_qb = inp.to_queenbee('test_input')
    assert inp_qb.default == 10
    assert inp_qb.annotations['__default_local__'] == 20
