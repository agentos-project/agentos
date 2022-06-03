from pcs.argument_set import ArgumentSet


def test_arg_set_equality():
    j = ArgumentSet(kwargs={"1": {"2": {"3": 4, "5": 6}}})
    k = ArgumentSet(kwargs={"1": {"2": {"5": 6, "3": 4}}})
    assert j == k

def test_arg_set_with_parent():
    x = ArgumentSet(args=[1,2], kwargs={3:4})
    y = ArgumentSet(parent=x, args=[5,6], kwargs={7:8})
    assert y.args == [1,2,5,6]
    assert y.kwargs == {3:4, 7:8}

    x.args = [9, 10]
    assert x.args == [9, 10]
    assert y.args == [9, 10, 5, 6]

    x.kwargs = {11: 12}
    assert x.kwargs == {11: 12}
    assert y.kwargs == {11: 12, 7: 8}

