from typing import TYPE_CHECKING

from pcs.spec_object import Component

# Avoids circular imports
if TYPE_CHECKING:
    from pcs.argument_set import ArgumentSet
    from pcs.component import Module
    from pcs.component_run import Output


class Command(Component):
    """
    A Command contains everything required to reproducibly execute a
    a method of a Module, Class, or Instance (technically the method is an
    attribute of a Python object that is created by a one of the Components
    of those types).

    Unlike a Run, a Command is not concerned with the outputs of the
    execution (see :py:func:`pcs.run.Run` for more on that.)
    TODO: rename Run to Results or something similar.

    You can think of a Command as a glorified dictionary containing the
    pointers to arguments and versions of code necessary to reproduce the
    setting up of a component (including its dependency dag) and the execution
    of one of its entry points with a specific ArgumentSet. Whereas a Run
    itself (which may contain a Command) is more like a client to a backing
    store used various types of outputs of the code being executed.

    Our concept of a Command is inspired by the MLflow ``Project Run``
    abstraction. In MLflow runs of Projects (which are roughly analogous to our
    Components) are intertwined with MLflow's concept of Runs for tracking
    purposes. In MLflow, a Project Run is a wrapper around an MLflow tracking
    Run.

    In MLflow, an entry point exists in the context of a Project Run. A
    project Run uses Tags on the underlying tracking run to log all sorts of
    metadata, including the entry point, per
    https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/projects/utils.py#L225
    and
    https://github.com/mlflow/mlflow/blob/v1.22.0/mlflow/utils/mlflow_tags.py
    """

    def __init__(
        self,
        component: "Module",
        function_name: str,
        argument_set: "ArgumentSet",
        log_return_value: bool,
    ):
        """
        Command constructor.

        :param component: The Component whose managed object we are going to
            call a function on.
        :param function_name: The function being run.
        :param argument_set: Arguments to be passed to the function being run.
        :param log_return_value: Whether or not to log the return value
            of the Entry point as part of this run. If True, the return
            value will be serialized to a file per the default value of
            the `return_value_log_format` parameter of
            `Module.run_with_arg_set()`. If the return value is a type
            that is not trivially serializable, you may want to set this
            to False.
        """
        super().__init__()
        self.component = component
        self.function_name = function_name
        self.argument_set = argument_set
        self.log_return_value = log_return_value
        self.register_attributes(
            ["component", "function_name", "argument_set", "log_return_value"]
        )

    def run(self) -> "Output":
        """
        Create a new run using the same root component, entry point, and
        params as this Command.

        :return: a new Command object representing the rerun.
        """
        return self.component.run_with_arg_set(
            self.entry_point,
            args=self.argument_set,
            log_return_value=self.log_return_value,
        )
