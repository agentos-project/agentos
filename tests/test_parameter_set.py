from agentos.parameter_set import ParameterSet


def test_param_set_equality():
    j = ParameterSet({"1": {"2": {"3": 4}}})
    k = ParameterSet({"1": {"2": {"3": 4}}})
    assert j == k


def test_param_set_updates():
    param_set = ParameterSet({"1": {"2": {"3": 4}}})
    param_set.update("1", "2", {"3": 5, "10": 11})
    assert param_set.get_component_params("1") == {"2": {"3": 5, "10": 11}}
    assert param_set.get_function_params("1", "2") == {"3": 5, "10": 11}
    assert param_set.get_param("1", "2", "3") == 5
