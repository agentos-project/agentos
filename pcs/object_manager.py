import abc
import logging
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

from pcs.argument_set import ArgumentSet
from pcs.command import Command
from pcs.component import Component
from pcs.output import Output
from pcs.registry import Registry

if TYPE_CHECKING:
    from pcs.python_executable import PythonExecutable

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class ObjectManager(Component, abc.ABC):
    """
    ObjectManagers manage an underlying Python object (i.e., a module, class,
    or class instance). They can also run a method that is an attribute on
    their underlying object. Runs can take an argument set.

    ObjectManagers provide reproducibility by returning an Output Component
    containing all of the dependencies of the Run, including: (1) the code of
    the object being run (i.e., ObjectManager) and the function_name, (2) the
    full DAG of other objects it depends on (i.e., DAG of other Components),
    (3) the set of arguments (literally a
    :py:func:`pcs.argument_set.ArgumentSet`) used during initialization of
    the managed object and all Components it transitively depends on.
    """

    def __init__(self):
        Component.__init__(self)
        self.active_output = None
        self._obj = None  # Set by get_object()

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
            arg_set=ArgumentSet(args=args, kwargs=kwargs),
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
        python_exec: "PythonExecutable" = None,
    ) -> Output:
        """
        Run the specified entry point a new instance of this Module's
        managed object given the specified arg_set, log the results
        and return the Run object.

        :param function_name: Name of a function to be called on a new
            instance of this component's managed object.
        :param arg_set: A :py:func:`pcs.argument_set.ArgumentSet` or
            ArgumentSet-like dict containing the function-name arguments,
            and/or arguments to be passed to the __init__() functions of this
            component's dependents during managed object initialization.
        :param publish_to: Optionally, publish the resulting Run object
            to the provided registry.
        :param log_return_value: If True, log the return value of the entry
            point being run.
        :param python_exec: A component representing the python executable
            to use when creating this object.
        :param return_value_log_format: Specify which format to use when
            serializing the return value. Only used if ``log_return_value``
            is True.
        """
        if python_exec:
            raise NotImplementedError
            # TODO: run the python runtime provided via subprocess and
            #       execute this run command inside of it.
            # TODO: return Output that was generated via that subprocess run.
        assert not self.active_output, (
            f"Module {self.identifier} already has an active_output, so a "
            "new run is not allowed."
        )
        arg_set = arg_set if arg_set else ArgumentSet()
        command = Command(self, function_name, arg_set, log_return_value)
        with Output.from_command(command) as output:
            for c in self.dependency_list():
                c.active_output = output
            with self as obj:
                res = self.call_function_with_arg_set(
                    obj, function_name, arg_set
                )
            if log_return_value:
                output.log_return_value(res, return_value_log_format)
            for c in self.dependency_list():
                c.active_output = None
            if publish_to:
                output.to_registry(publish_to)
            del obj  # Any virtual_envs that were activated are deactivated.
            return output

    def call_function_with_arg_set(
        self, instance: Any, function_name: str, arg_set: ArgumentSet
    ) -> Any:
        fn = getattr(instance, function_name)
        assert fn is not None, f"{instance} has no attr {function_name}"
        logger.debug(
            f"Calling {self.identifier}.{function_name} with "
            f"args: {arg_set.args} and kwargs: {arg_set.kwargs})"
        )
        result = fn(*arg_set.get_arg_objs(), **arg_set.get_kwarg_objs())
        return result

    def __enter__(self) -> Any:
        return self.get_object(force_new=True)

    def __exit__(self, type, value, traceback) -> None:
        self.reset_object()

    def get_object(self, force_new: bool = False) -> Any:
        if not self._obj or force_new:
            self._obj = self.get_new_object()
        return self._obj

    @abc.abstractmethod
    def get_new_object(self) -> Any:
        raise NotImplementedError

    def reset_object(self):
        if self._obj:
            self._obj = None

    @abc.abstractmethod
    def freeze(self: T, force: bool = False) -> T:
        """
        Return a copy of self whose parent Module (or self if this is a Module)
        is versioned.
        """
        raise NotImplementedError
