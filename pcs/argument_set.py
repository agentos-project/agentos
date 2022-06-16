from typing import Any, Dict, List, Optional, Tuple, Union

from pcs.component import Component
from pcs.utils import copy_find_and_replace_leaves


class ArgumentSet(Component):
    """
    Encapsulate a set of arguments for a function call.
    """

    def __init__(
        self,
        args: Union[Tuple[Any], List[Any]] = None,
        kwargs: Dict[Any, Any] = None,
        parent: Optional["ArgumentSet"] = None,
    ):
        super().__init__()
        self._args = list(args) if args else []
        self._kwargs = kwargs if kwargs else {}
        self.parent = parent
        self.register_attributes(["args", "kwargs", "parent"])

    @property
    def args(self):
        args = []
        if self.parent:
            args = args + self.parent.args
        return args + self._args

    @args.setter
    def args(self, value):
        self._args = value

    @property
    def kwargs(self):
        kwargs = {}
        if self.parent:
            kwargs.update(self.parent.kwargs)
        if self._kwargs:
            kwargs.update(self._kwargs)
        return kwargs

    @kwargs.setter
    def kwargs(self, value):
        self._kwargs = value
        print(f"kwargs updated to {value}")

    @staticmethod
    def _resolve_objs(data_structure: Any):
        from pcs.object_manager import ObjectManager

        _, updated_struct = copy_find_and_replace_leaves(
            data_structure,
            lambda leaf: isinstance(leaf, ObjectManager),
            lambda leaf: leaf.get_object(),
        )
        return updated_struct

    def get_arg_objs(self):
        return self._resolve_objs(self.args)

    def get_kwarg_objs(self):
        return self._resolve_objs(self.kwargs)
