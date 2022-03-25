from pcs.argument_set import ArgumentSet
from pcs.component import Component
from pcs.registry import InMemoryRegistry


class Simple:
    def __init__(self, x):
        self._x = x

    def fn(self, input):
        return self._x, input


def test_component_instance_run():
    arg_set = ArgumentSet(
        {"Simple": {"__init__": {"x": 1}, "fn": {"input": "hi"}}}
    )
    c = Component.from_class(Simple, instantiate=True)
    run = c.run_with_arg_set("fn", arg_set)
    assert run.run_command.component == c
    assert run.run_command.entry_point == "fn"
    new_run = run.run_command.run()
    assert new_run.run_command.component == c

    registry = InMemoryRegistry()
    run.run_command.to_registry(registry)
    assert (
        registry.get_run_command_spec(run.run_command.identifier)
        == run.run_command.to_spec()
    )

    registry.add_run_spec(run.to_spec())
    fetched_run_spec = registry.get_run_spec(run.identifier)
    assert fetched_run_spec == run.to_spec()


def test_run_tracking():
    from pcs.run import Run

    run = Run()
    assert run.identifier == run._mlflow_run.info.run_id
    run.log_metric("test_metric", 1)
    assert run.data.metrics["test_metric"] == 1
    run.set_tag("test_tag", "tag_val")
    assert run.data.tags["test_tag"] == "tag_val"
