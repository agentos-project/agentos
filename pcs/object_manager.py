import abc
import logging
from functools import partial
from typing import Any, TypeVar

from pcs.argument_set import ArgumentSet
from pcs.command import Command
from pcs.component import Component
from pcs.output import Output
from pcs.registry import Registry

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ObjectManager(abc.ABC, Component):
    """
    ObjectManagers manage an underlying Python object (i.e. a module, class,
    or class instance). They can also run a method that is an attribute on
    their underlying object. Runs can take an argument set.
    """

    def __init__(self):
        Component.__init__(self)
        self.active_output = None

    def get_default_function_name(self):
        try:
            imported_obj = self.get_object()
            function_name = imported_obj.DEFAULT_ENTRY_POINT
        except AttributeError:
            function_name = "run"
        return function_name

    def __getattr__(self, attr_name):
        if attr_name != "run_with_arg_set" and attr_name.startswith("run_"):
            function_name = attr_name[4:]
            return partial(self.run, function_name)
        else:
            raise AttributeError(
                f"type object '{self.__class__}' has no attribute "
                f"'{attr_name}'"
            )

    def run(self, function_name: str, *args, **kwargs):
        """
        Run an entry point with provided arguments. If you need to specify
        arguments to the init function of the managed object or any of
        its dependency components, use :py:func:`run_with_arg_set`.

        :param function_name: name of function to call on manage object.
        :param kwargs: keyword-only args to pass through to managed object
            function called function-name.
        :return: the return value of the entry point called.
        """
        run = self.run_with_arg_set(
            function_name,
            arg_set=ArgumentSet(args, kwargs),
            log_return_value=True,
        )
        return run.return_value

    def run_with_arg_set(
        self,
        function_name: str,
        arg_set: ArgumentSet = None,
        publish_to: Registry = None,
        log_return_value: bool = True,
        return_value_log_format: str = "yaml",
    ) -> Output:
        """
        Run the specified entry point a new instance of this Module's
        managed object given the specified arg_set, log the results
        and return the Run object.

        :param function_name: Name of a function to be called on a new
            instance of this component's managed object.
        :param arg_set: A :py:func:`pcs.argument_set.ArgumentSet` or
            ArgumentSet-like dict containing the function-name arguments, and/or
            arguments to be passed to the __init__() functions of this
            component's dependents during managed object initialization.
        :param publish_to: Optionally, publish the resulting Run object
            to the provided registry.
        :param log_return_value: If True, log the return value of the entry
            point being run.
        :param return_value_log_format: Specify which format to use when
            serializing the return value. Only used if ``log_return_value``
            is True.
        """
        assert not self.active_output, (
            f"Module {self.identifier} already has an active_output, so a "
            "new run is not allowed."
        )
        arg_set = arg_set if arg_set else ArgumentSet()
        command = Command(self, function_name, arg_set, log_return_value)
        with Output.from_command(command) as output:
            for c in self.dependency_list():
                c.active_output = output
            obj = self.get_object()
            res = self.call_function_with_arg_set(obj, function_name, arg_set)
            if log_return_value:
                output.log_return_value(res, return_value_log_format)
            for c in self.dependency_list():
                c.active_output = None
            if publish_to:
                output.to_registry(publish_to)
            return output

    def call_function_with_arg_set(
        self, instance: Any, function_name: str, arg_set: ArgumentSet
    ) -> Any:
        fn = getattr(instance, function_name)
        assert fn is not None, f"{instance} has no attr {function_name}"
        print(
            f"Calling {self.identifier}.{function_name} with "
            f"args: {arg_set.args} and kwargs: {arg_set.kwargs})"
        )
        result = fn(*arg_set.get_arg_objs(), **arg_set.get_kwarg_objs())
        return result

    @abc.abstractmethod
    def get_object(self) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def freeze(self: T, force: bool = False) -> T:
        """
        Return a copy of self whose parent Module (or self if this is a Module)
        is versioned.
        """
        raise NotImplementedError
