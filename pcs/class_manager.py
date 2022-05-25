import copy
import logging
import sys
from hashlib import sha1
from pathlib import Path
from typing import Type, TypeVar

from dill.source import getsource as dill_getsource

from pcs.object_manager import ObjectManager
from pcs.module_manager import Module
from pcs.repo import Repo, LocalRepo
from pcs.argument_set import ArgumentSet

logger = logging.getLogger(__name__)

# Use Python generics (https://mypy.readthedocs.io/en/stable/generics.html)
T = TypeVar("T")


class Class(ObjectManager):
    def __init__(self, module: Module, name: str, **other_dependencies):
        super().__init__()
        for k, v in other_dependencies.items():
            setattr(self, k, v)
        self.register_attributes(other_dependencies.keys())
        self.module = module
        self.name = name
        self.register_attributes(["module", "name"])

    @classmethod
    def from_class(
        cls,
        class_obj: Type[T],
        repo: Repo = None,
    ) -> "Module":
        name = class_obj.__name__
        if class_obj.__module__ == "__main__":
            # handle classes defined in REPL.
            file_contents = dill_getsource(class_obj)
            if not repo:
                repo = LocalRepo()
            sha = str(int(sha1(file_contents.encode("utf-8")).hexdigest(), 16))
            src_file = repo.get_local_repo_dir() / f"{name}-{sha}.py"
            if src_file.exists():
                print(f"Re-using existing source file {src_file}.")
            else:
                with open(src_file, "x") as f:
                    f.write(file_contents)
                print(f"Wrote new source file {src_file}.")
        else:
            managed_obj_module = sys.modules[class_obj.__module__]
            assert hasattr(managed_obj_module, name), (
                "Components can only be created from classes that are "
                "available as an attribute of their module."
            )
            src_file = Path(managed_obj_module.__file__)
            logger.debug(
                f"Handling class_obj {name} from existing "
                f"source file {src_file}."
            )
            repo = LocalRepo(path=src_file.parent)
            logger.debug(
                f"Created LocalRepo {repo.identifier} from existing source "
                f"file {src_file}."
            )

        return cls(
            module=Module(repo=repo, file_path=src_file.name),
            name=name,
        )

    def get_object(self):
        module = self.module.get_object()
        return getattr(module, self.name)

    def instantiate(self, argument_set: ArgumentSet, name: str = None):
        from pcs.instance_manager import Instance

        return Instance(self, argument_set=argument_set, name=name)

    def freeze(self: T, force: bool = False) -> T:
        self_copy = copy.deepcopy(self)
        self_copy.module = self.module.freeze(force)
        return self_copy