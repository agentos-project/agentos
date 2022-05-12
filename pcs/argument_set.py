from typing import Any, Dict, List

from pcs.spec_object import Component


class ArgumentSet(Component):
    """
    Encapsulate a set of arguments for a function call.
    """
    def __init__(self, args: List[Any] = None, kwargs: Dict[Any, Any] = None):
        super().__init__()
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}
        self.register_attributes(["args", "kwargs"])
