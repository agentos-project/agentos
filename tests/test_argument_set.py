from pcs.argument_set import ArgumentSet


def test_arg_set_equality():
    j = ArgumentSet(kwargs={"1": {"2": {"3": 4, "5": 6}}})
    k = ArgumentSet(kwargs={"1": {"2": {"5": 6, "3": 4}}})
    assert j == k
