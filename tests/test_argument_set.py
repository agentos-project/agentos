from pcs.argument_set import ArgumentSet


def test_arg_set_equality():
    j = ArgumentSet({"1": {"2": {"3": 4}}})
    k = ArgumentSet({"1": {"2": {"3": 4}}})
    assert j == k


def test_arg_set_updates():
    arg_set = ArgumentSet({"1": {"2": {"3": 4}}})
    arg_set.update("1", "2", {"3": 5, "10": 11})
    assert arg_set.get_component_args("1") == {"2": {"3": 5, "10": 11}}
    assert arg_set.get_function_args("1", "2") == {"3": 5, "10": 11}
    assert arg_set.get_arg("1", "2", "3") == 5
