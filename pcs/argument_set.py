import copy
from typing import Any, Dict, List, Tuple, Union

from pcs.component import Component
from pcs.utils import find_and_replace_leaves


class ArgumentSet(Component):
    """
    Encapsulate a set of arguments for a function call.
    """

    def __init__(
        self,
        args: Union[Tuple[Any], List[Any]] = None,
        kwargs: Dict[Any, Any] = None,
    ):
        super().__init__()
        self.args = list(args) if args else []
        self.kwargs = kwargs if kwargs else {}
        self.register_attributes(["args", "kwargs"])

    @staticmethod
    def _resolve_objs(data_structure: Any):
        from pcs.object_manager import ObjectManager

        find_and_replace_leaves(
            data_structure,
            lambda leaf: isinstance(leaf, ObjectManager),
            lambda leaf: leaf.get_object(),
        )

    def get_arg_objs(self):
        resolved_args = copy.deepcopy(self.args)
        self._resolve_objs(resolved_args)
        return resolved_args

    def get_kwarg_objs(self):
        resolved_args = copy.deepcopy(self.kwargs)
        self._resolve_objs(resolved_args)
        return resolved_args
