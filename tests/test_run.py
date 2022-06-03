from pcs import Class
from pcs.argument_set import ArgumentSet
from pcs.registry import InMemoryRegistry


class Simple:
    def __init__(self, x):
        self._x = x

    def fn(self, input):
        return self._x, input


def test_component_instance_run():
    simple_arg_set = ArgumentSet(kwargs={"x": 1})
    fn_arg_set = ArgumentSet(kwargs={"input": "hi"})
    i = Class.from_class(Simple).instantiate(simple_arg_set)
    output = i.run_with_arg_set("fn", fn_arg_set)
    assert output.command.component == i
    assert output.command.function_name == "fn"
    new_output = output.command.run()
    assert new_output.command.component == i

    registry = InMemoryRegistry()
    output.command.to_registry(registry)
    assert (
        registry.get_spec(output.command.identifier)
        == output.command.to_spec()
    )

    registry.add_spec(output.to_spec())
    fetched_output_spec = registry.get_spec(output.identifier)
    assert fetched_output_spec == output.to_spec()


def test_run_tracking():
    from pcs.mlflow_run import MLflowRun

    run = MLflowRun()
    run.log_metric("test_metric", 1)
    assert run.data["metrics"]["test_metric"] == 1
    run.set_tag("test_tag", "tag_val")
    assert run.data["tags"]["test_tag"] == "tag_val"
