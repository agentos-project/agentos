import copy
from typing import TypeVar

from pcs.class_manager import ArgumentSet, Class
from pcs.object_manager import ObjectManager
from pcs.utils import find_and_replace_leaves

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Instance(ObjectManager):
    """
    An Instance Component is very similar to a Class Component. The difference
    is that for an Instance, the underlying class is instantiated during
    initialization of the component.
    """

    def __init__(
        self,
        instance_of: Class,
        argument_set: ArgumentSet = None,
    ):
        super().__init__()
        self.instance_of = instance_of
        self.argument_set = argument_set if argument_set else ArgumentSet()
        self.register_attributes(["instance_of", "argument_set"])
        self._instance = None

    def get_object(self):
        if self._instance:
            return self._instance
        else:
            cls = self.instance_of.get_object()
            self._instance = cls(
                *self.argument_set.get_arg_objs(),
                **self.argument_set.get_kwarg_objs()
            )
            setattr(self._instance, "__component__", self)
            return self._instance

    def freeze(self: T, force: bool = False) -> T:
        self_copy = self.copy()
        self_copy.instance_of = self.instance_of.freeze(force)
        for i in [self_copy.argument_set.args, self_copy.argument_set.kwargs]:
            find_and_replace_leaves(
                i,
                lambda x: isinstance(x, ObjectManager),
                lambda x: x.freeze(force),
            )
        return self_copy
