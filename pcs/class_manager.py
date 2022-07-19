import copy
import logging
import sys
from hashlib import sha1
from pathlib import Path
from typing import Type, TypeVar

from dill.source import getsource as dill_getsource

from pcs.argument_set import ArgumentSet
from pcs.module_manager import Module, FileModule
from pcs.object_manager import ObjectManager
from pcs.repo import LocalRepo, Repo

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
    ) -> "Class":
        name = class_obj.__name__
        if class_obj.__module__ == "__main__":
            # handle classes defined in REPL.
            file_contents = dill_getsource(class_obj)
            if not repo:
                repo = LocalRepo()
            sha = str(int(sha1(file_contents.encode("utf-8")).hexdigest(), 16))
            src_file = repo.get_local_file_path(f"{name}-{sha}.py")
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
            module=FileModule(repo=repo, file_path=src_file.name),
            name=name,
        )

    def get_new_object(self):
        module = self.module.get_object(force_new=True)
        cls = getattr(module, self.name)
        setattr(cls, "__component__", self)
        return cls

    def reset_object(self):
        self.module.reset_object()
        super().reset_object()

    def instantiate(self, argument_set: ArgumentSet):
        from pcs.instance_manager import Instance

        return Instance(self, argument_set=argument_set)

    def freeze(self: T, force: bool = False) -> T:
        self_copy = self.copy()
        self_copy.module = self_copy.module.freeze(force)
        return self_copy
