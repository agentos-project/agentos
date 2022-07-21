import abc
import json
import logging
import os
import pprint
import shutil
import tarfile
import tempfile
from collections import defaultdict, deque
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)
from uuid import uuid4

import requests
import yaml
from deepdiff import DeepDiff
from dotenv import load_dotenv

from pcs.specs import Spec, flatten_spec, is_flat_spec, unflatten_spec
from pcs.utils import (
    IDENTIFIER_REF_PREFIX,
    extract_identifier,
    filter_leaves,
    is_identifier,
    is_spec_body,
    make_identifier_ref,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pcs.component import Component
    from pcs.repo import Repo

DEFAULT_REG_FILE = "components.yaml"
DEFAULT_WEB_URL = "https://aos-web.herokuapp.com"
DEFAULT_LOCAL_URL = "http://localhost:8000"
WEB_API_EXTENSION = "/api/v1"


class Registry(abc.ABC):
    @staticmethod
    def from_dict(input_dict: Dict) -> "Registry":
        return InMemoryRegistry.from_dict(input_dict)

    @staticmethod
    def from_yaml(file_path: str) -> "Registry":
        with open(file_path) as file_in:
            config = yaml.safe_load(file_in)
        reg = InMemoryRegistry.from_dict(
            config, base_path=Path(file_path).parent
        )
        return reg

    @staticmethod
    def from_yamls(file_paths: List[str]) -> "Registry":
        SPECS_KEY = InMemoryRegistry.SPECS_KEY
        ALIASES_KEY = InMemoryRegistry.ALIASES_KEY
        input_dict = {SPECS_KEY: {}, ALIASES_KEY: {}}
        parent_path = Path(file_paths[0]).parent
        for path in file_paths:
            # TODO(andyk): Remove this constraint.
            assert (
                Path(path).parent == parent_path
            ), "all registry yaml files must be in the same dir."
            with open(path) as f:
                file_dict = yaml.safe_load(f)
                if SPECS_KEY in file_dict:
                    input_dict[SPECS_KEY].update(file_dict[SPECS_KEY])
                if ALIASES_KEY in file_dict:
                    input_dict[ALIASES_KEY].update(file_dict[ALIASES_KEY])
        reg = InMemoryRegistry.from_dict(input_dict, parent_path)
        return reg

    @classmethod
    def from_file_in_repo(
        cls, repo: "Repo", file_path: str, format: str = "yaml"
    ) -> "Registry":
        """
        Read in a registry file from a repo.

        :param repo: Repo to load registry file from.
        :param file_path: Path within Repo that registry is located, relative
            to the repo root.
        :param format: Optionally specify the format of the registry file.
        :return: a new Registry object.
        """
        assert format == "yaml", (
            f"{format} not supported. YAML is the only registry file format "
            "supported currently"
        )
        return cls.from_yaml(repo.get() / file_path)

    @classmethod
    def from_repo_inferred(
        cls,
        repo: "Repo",
        py_file_suffixes: Tuple[str] = (".py", ".python"),
        requirements_file: str = "requirements.txt",
    ):
        from pcs.module_manager import FileModule  # Avoid circular ref.

        reg = InMemoryRegistry()
        # get list of python files in Repo
        py_files = set()
        for suff in py_file_suffixes:
            found = repo.get().rglob(f"*{suff}")
            py_files = py_files.union(set(found))
        virtual_env_component = None
        if repo.get_local_file_path(requirements_file).is_file():
            from pcs.path import RelativePath  # Avoid circular import.
            from pcs.virtual_env import VirtualEnv

            virtual_env_component = VirtualEnv(
                requirements_files=[
                    RelativePath(
                        repo=repo,
                        relative_path=str(requirements_file),
                    )
                ]
            )
        # create and register FileModule components
        for f in py_files:
            relative_path = f.relative_to(repo.get())
            module_kwargs = {
                "repo": repo,
                "file_path": str(relative_path).replace("\\", "/"),
            }
            if virtual_env_component:
                module_kwargs.update(
                    {"virtual_env": virtual_env_component.identifier}
                )
            mod_component = FileModule(**module_kwargs)
            # TODO: add dependencies to component for every import
            #       statement in the file (or just the ones at the
            #       module level?)
            mod_component.to_registry(reg)
        return reg
        # TODO: finish this, add class components & class instance components?

    @classmethod
    def from_repo(cls, repo: "Repo"):
        """
        Get a registry from a Repo. If the Repo has a default registry file,
        use that, if not infer specs by inspecting the contents of the repo.
        """
        if DEFAULT_REG_FILE in repo:
            return cls.from_file_in_repo(DEFAULT_REG_FILE)
        return cls.from_repo_inferred(repo)

    @classmethod
    def from_default(cls):
        if not hasattr(cls, "_default_registry"):
            load_dotenv()
            url = DEFAULT_WEB_URL
            if os.getenv("USE_LOCAL_SERVER", False):
                url = DEFAULT_LOCAL_URL
            elif os.getenv("DEFAULT_REGISTRY_URL", False):
                url = os.getenv("DEFAULT_REGISTRY_URL")
            cls._default_registry = WebRegistry(f"{url}{WEB_API_EXTENSION}")
        return cls._default_registry

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        raise NotImplementedError

    def to_yaml(self, filename: str = None, mode: str = "w") -> None:
        if filename:
            with open(filename, mode=mode) as file:
                yaml.dump(self.to_dict(), file)
        else:
            return yaml.dump(self.to_dict())

    @property
    @abc.abstractmethod
    def specs(self) -> Mapping:
        raise NotImplementedError

    def __contains__(self, identifier: str):
        return identifier in self.specs

    def __getitem__(self, identifier):
        return self.specs[identifier]

    def get_spec(
        self,
        identifier: str,
        flatten: bool = False,
        error_if_not_found: bool = True,
    ) -> Optional[Spec]:
        """
        Returns the spec dict with ``identifier`` if it exists, or raise an
        Error (or optionally, return None) if it does not. Registries are not
        allowed to contain multiple specs with the same identifier.

        :param identifier: The identifier of the component to fetch.
        :param flatten: If True, flatten the outermost 2 layers of nested
            dicts into a single dict. In an unflattened component spec, the
            outermost dict is from identifier (which is a hash string)
            to component properties. In a flattened Module spec, the
            identifier is included in the dictionary with the other component
            attributes.
        :param error_if_not_found: Set to False to return an empty dict in
            the case that a matching component is not found in this registry.

        :returns: the spec dict with the identifier provided, if it exists
            in this registry, otherwise either return None or throw an Error,
            depending on whether error_if_not_found is True or False.

        """
        if identifier in self.specs:
            body = self.specs[identifier]
        elif identifier in self.aliases:
            body = self.specs[self.aliases[identifier]]
        elif error_if_not_found:
            raise LookupError(
                f"'{identifier}' did not match any identifiers or aliases "
                f"in this registry {self.to_dict()}"
            )
        else:
            return None
        spec = Spec.from_body(body)
        return spec.to_flat() if flatten else spec

    def get_specs_transitively_by_id(
        self,
        identifier: str,
        flatten: bool = True,
    ) -> (Sequence[Dict], Sequence[Dict]):
        component_identifiers = [identifier]
        repo_specs = {}
        component_specs = {}
        while component_identifiers:
            c_id = component_identifiers.pop()
            c_spec = self.get_spec(c_id, flatten=flatten)
            inner_spec = c_spec if flatten else c_spec[c_id]
            component_specs[c_id] = c_spec
            repo_id = inner_spec["repo"]
            repo_spec = self.get_spec(repo_id, flatten=flatten)
            repo_specs[repo_id] = repo_spec
            for d_id in inner_spec.get("dependencies", {}).values():
                component_identifiers.append(d_id)
        return list(component_specs.values()), list(repo_specs.values())

    @property
    @abc.abstractmethod
    def aliases(self) -> Mapping:
        raise NotImplementedError

    @abc.abstractmethod
    def add_spec(self, spec: Dict) -> None:
        raise NotImplementedError

    def add_component(
        self, component: "Component", recurse: bool = True
    ) -> None:
        component.to_registry(self, recurse=recurse)

    @abc.abstractmethod
    def add_alias(self, alias: str, identifier: str) -> None:
        raise NotImplementedError

    def update(self, other_registry) -> None:
        for ident, body in other_registry.specs.items():
            self.add_spec({ident: body})
        for alias, i in other_registry.aliases.items():
            if alias in self.aliases:
                assert self.aliases[alias] == i
            else:
                self.add_alias(alias, i)

    def replace_spec(self, identifier, new_spec):
        raise NotImplementedError


class InMemoryRegistry(Registry):
    """
    A mutable in-memory registry.
    """

    SPECS_KEY = "specs"
    ALIASES_KEY = "aliases"

    def __init__(self):
        self._registry = {self.SPECS_KEY: {}, self.ALIASES_KEY: {}}
        self._init_helper_dicts()

    def _init_helper_dicts(self):
        # Setup helper dicts (for performance).
        self._dependee_ids = defaultdict(
            set
        )  # {id: set(ids that depend on it)}
        self._dependency_ids = defaultdict(
            set
        )  # {id: set(ids that it depends on)}

    @classmethod
    def from_dict(
        cls, input_dict: Dict, base_path: Path = None
    ) -> "InMemoryRegistry":
        reg = cls()
        for key in input_dict.keys():
            assert key == reg.SPECS_KEY or key == reg.ALIASES_KEY, (
                f"'input_dict' can not have top level level keys besides "
                f"'{reg.SPECS_KEY}' and '{reg.ALIASES_KEY}', but this "
                f"has '{key}'."
            )
        if cls.ALIASES_KEY in input_dict:
            reg._registry[cls.ALIASES_KEY] = input_dict[cls.ALIASES_KEY]
        if cls.SPECS_KEY in input_dict:
            reg._registry[cls.SPECS_KEY] = input_dict[cls.SPECS_KEY]
        reg._resolve_inline_spec_bodies()
        reg._resolve_aliases()
        reg._update_helpers()
        if base_path:
            reg._make_relative_local_repo_paths_absolute(base_path)
        reg._resolve_alias_references()
        reg._update_helpers()
        return reg

    def _update_helpers(self, specs_dict: Dict = None) -> None:
        if specs_dict:
            specs_dict = specs_dict
        else:
            self._init_helper_dicts()
            specs_dict = self.specs
        for ident, spec_body in specs_dict.items():
            for _, spec_ref in filter_leaves(
                spec_body,
                lambda x: type(x) == str
                and x.startswith(IDENTIFIER_REF_PREFIX),
            ).items():
                ref_id = extract_identifier(spec_ref)
                self._dependee_ids[ref_id].add(ident)
                self._dependency_ids[ident].add(ref_id)

    def _remove_spec(self, identifier: str) -> None:
        """
        Removes spec and updates helper dicts to remove the edges they
        are tracking between the spec and its dependencies.
        """
        spec_body = self._registry[self.SPECS_KEY].pop(identifier)
        for _, spec_ref in filter_leaves(
            spec_body,
            lambda x: type(x) == str and x.startswith(IDENTIFIER_REF_PREFIX),
        ).items():
            ref_id = extract_identifier(spec_ref)
            self._dependee_ids[ref_id].remove(identifier)
            self._dependency_ids[identifier].remove(ref_id)

    @property
    def specs(self) -> Mapping:
        return self._registry[self.SPECS_KEY]

    @property
    def aliases(self) -> Mapping:
        return self._registry.get(self.ALIASES_KEY, {})

    def identifier_to_aliases(self, identifier):
        return [
            alias for alias, hash in self.aliases.items() if hash == identifier
        ]

    def _resolve_inline_spec_bodies(self) -> Dict:
        """
        Allow developers to specify specs "in-line", i.e., in a nested form.
        This will rewrite those in a non-nested form. So, for example,
        resolve the following::

            specs:
                c6af7bc9d07271dfe75429ac8ee34398dfdc4338:
                    nested_spec1:
                        type: ComponentType1  # inline spec body
                        nested_spec2:
                            type: ComponentType2  # inline spec body
                            key2: val2
                    non_spec_dict:
                        - type: ComponentType3  # inline spec body
                          key3: val3
                        - "a string"

        ...into::

            specs:
                c6af7bc9d07271dfe75429ac8ee34398dfdc4338:
                    nested_spec1: spec:271dfe754c6af7bc9d0729adfdc4338c8ee34398
                    non_spec_dict:
                        - spec:64d0729adf2e75caf7bc971d4398dc43cf883e3e
                        - "a string"

                271dfe754c6af7bc9d0729adfdc4338c8ee34398:
                    type: ComponentType1
                    nested_spec2: spec:e75caf7bc964d0729adf271df838ee34398dc43c

                e75caf7bc964d0729adf271df838ee34398dc43c:
                    type: ComponentType2
                    key2: val2

                64d0729adf2e75caf7bc971d4398dc43cf883e3e:
                    type: ComponentType3
                    key3: val3

        """
        new_specs = {}
        to_handle = []
        # Handle first layer of specs.
        for ident, body in self.specs.items():
            assert is_spec_body(body)
            new_specs[ident] = {}
            for k, v in body.items():
                to_handle.append((new_specs[ident], k, v))
        rand_alias_prefix = "alias_"
        while to_handle:
            struct, key, elt = to_handle.pop()
            if is_spec_body(elt):  # handle inline spec body
                alias = rand_alias_prefix + str(uuid4())
                struct[key] = make_identifier_ref(alias)
                new_specs[alias] = {}
                for k, v in elt.items():
                    to_handle.append((new_specs[alias], k, v))
            elif elt and isinstance(elt, dict):  # handle non-spec body dict
                try:
                    if struct[key] is None:
                        struct[key] = {}
                except (IndexError, KeyError):
                    struct[key] = {}
                for attr_key, attr_val in elt.items():
                    to_handle.append((struct[key], attr_key, attr_val))
            elif elt and isinstance(elt, list):  # handling list
                try:
                    struct[key]
                except (IndexError, KeyError):
                    struct[key] = [None] * len(elt)
                for i, sub_elt in enumerate(elt):
                    to_handle.append((struct[key], i, sub_elt))
            else:  # elt must be leaf
                struct[key] = elt

        self._registry[self.SPECS_KEY] = new_specs

    def _resolve_aliases(self) -> None:
        """
        To make it easier for developers to write specs, we allow for
        the input dictionary to have specs where the identifier is an
        arbitrary string. We assume that any spec identifier that is not
        currently a valid hash is an alias (i.e a 1-1 mapping for the hash
        of the contents of the spec) and we resolve the dictionary by replacing
        the string provided with the correct hash identifier of the underlying
        spec contents dict and then updating the aliases section of the
        registry with the string provided. E.g.,::

            specs:
                my_alias:  # Must be a spec, i.e.: have 'type' attr.
                    type: MyComponentType
                    other: my_2nd_alias
                my_2nd_alias:
                    type: MyComponentType

        ...will be transformed into::

            specs:
                c6af7bc9d07271dfe75429ac8ee34398dfdc4338:
                    type: MyComponentType
                    other: d076af7bc92c71dfe754293fdc43384398dac8ee
                d076af7bc92c71dfe754293fdc43384398dac8ee:
                    type: MyComponentType
            aliases:
                my_alias: c6af7bc9d07271dfe75429ac8ee34398dfdc4338
                my_2nd_alias: d076af7bc92c71dfe754293fdc43384398dac8ee

        """
        new_specs = {}
        new_aliases = self.aliases if self.aliases else {}
        from pcs.component import Component  # Avoid circular import.

        for id_or_alias, body in self.specs.items():
            assert is_spec_body(body), (
                "Trying to resolve aliases in something that is not a spec "
                f"body: {body}"
            )
            hash = Component.spec_body_to_identifier(body)
            if is_identifier(id_or_alias):
                new_specs[id_or_alias] = body
            else:
                if id_or_alias in new_aliases:
                    assert new_aliases[id_or_alias] == hash
                else:
                    new_aliases[id_or_alias] = hash
                new_specs[hash] = body
        self._registry[self.SPECS_KEY] = new_specs

        if new_aliases:
            self._registry[self.ALIASES_KEY] = new_aliases

    def _resolve_alias_references(self):
        from pcs.component import Component  # Avoid circular import.

        # replace uses of aliases within spec bodies.
        to_resolve = [Spec.from_body(body) for body in self.specs.values()]
        while to_resolve:
            curr_spec = to_resolve.pop()
            component = Component.from_spec(curr_spec, self)
            component.to_registry(self)
            self._update_aliases(curr_spec.identifier, component.identifier)

    def _update_aliases(self, ident_to_replace, new_identifier):
        """
        Change all aliases that currently point to `ident_to_replace` to
        instead point to `new_identifier`.
        """
        aliases_to_update = [
            alias
            for alias, ident in self.aliases.items()
            if ident == ident_to_replace
        ]
        for alias in aliases_to_update:
            self.aliases[alias] = new_identifier

    def _make_relative_local_repo_paths_absolute(self, base_path: str) -> None:
        updated_specs = []
        for spec_id, spec_body in self.specs.items():
            if spec_body["type"] == "LocalRepo":
                p = PurePath(spec_body["path"])
                if not p.is_absolute():
                    abs_path = (base_path / p).resolve()
                    updated_spec = Spec.from_body(spec_body)
                    updated_spec.update_body({"path": str(abs_path)})
                    updated_specs.append((spec_id, updated_spec))
        for old_id, updated in updated_specs:
            self.replace_spec(old_id, updated)

    def add_spec(self, spec: Spec) -> None:
        if not isinstance(spec, Spec):
            spec = Spec(input_dict=spec)
        if spec.identifier in self.specs:
            spec_diff = DeepDiff(spec.body, self.specs[spec.identifier])
            assert not spec_diff, (
                f"Spec {spec.identifier} exists in registry and is "
                f"different:\n\n{spec_diff}"
            )
            logger.debug(
                f"Spec {spec.identifier} is already in registry; "
                "nothing to do."
            )
        self._registry[self.SPECS_KEY].update(spec)
        self._update_helpers(spec)

    def add_alias(self, alias: str, identifier: str) -> None:
        self._registry[self.ALIASES_KEY][alias] = identifier

    def to_dict(self) -> Dict:
        return self._registry

    def replace_spec(
        self, identifier: str, new_spec: Dict, remove_old_spec: bool = True
    ):
        """
        Adds replacements for, but does not remove, spec with `identifier`
        and all of its ancestors.

        Summary of the algorithm:
            - add new node and update its child (i.e., dependency) edges
            - push new nodes parents' ids onto queue
            - while queue not empty:
                - x = queue.dequeue()
                - update edges between x and its children (dependencies)
                - enqueue ids of its parents
        """
        if type(new_spec) != Spec:
            new_spec = Spec(input_dict=new_spec)
        while identifier in self.aliases:
            identifier = self.aliases[identifier]
        # add the new node (which updates helpers) and enqueue its new parents.
        self.add_spec(new_spec)
        self._update_aliases(identifier, new_spec.identifier)
        parent_ids = self._dependee_ids[identifier]
        replacements_to_do = deque(parent_ids)
        if remove_old_spec:
            self._remove_spec(identifier)
        old_ident_to_new = {identifier: new_spec.identifier}

        while replacements_to_do:
            # dequeue ident of spec that is being replaced
            id_to_replace = replacements_to_do.popleft()
            while id_to_replace in old_ident_to_new:
                id_to_replace = old_ident_to_new[id_to_replace]
            replacement_spec = Spec.from_body(self.specs[id_to_replace])
            # find and enqueue its parents
            replacements_to_do += self._dependee_ids[id_to_replace]
            # Update body of spec replacing all child refs found in old_to_new,
            # making sure to follow references in old_to_new till no more are
            # found.
            children_to_update = set()
            for dependency_id in self._dependency_ids[id_to_replace]:
                new_ident = dependency_id
                while new_ident in old_ident_to_new:
                    new_ident = old_ident_to_new[new_ident]
                if new_ident != dependency_id:
                    replacement_spec.replace_in_body(
                        lambda x: x == make_identifier_ref(dependency_id),
                        lambda x: make_identifier_ref(new_ident),
                    )
                    children_to_update.add(new_ident)
            # Store new mapping into old_to_new
            if id_to_replace != replacement_spec.identifier:
                old_ident_to_new[id_to_replace] = replacement_spec.identifier
            # Update `dependee_ids` helper dict since this node's children
            # didn't know the new identifier of their to-be-updated parents
            # when they were added to the graph, so we couldn't have updated
            # the helper dicts at that time.
            for child_id in children_to_update:
                self._dependee_ids[child_id].add(replacement_spec.identifier)
            # add new spec (identifier->updated_body) to graph
            self.add_spec(replacement_spec)
            if remove_old_spec:
                self._remove_spec(id_to_replace)
            # update aliases
            self._update_aliases(id_to_replace, replacement_spec.identifier)


class WebRegistry(Registry):
    """
    A web-server backed Registry.
    """

    SPEC_RESPONSE_BODY_KEY = "body"

    def __init__(self, root_api_url: str):
        self.root_api_url = root_api_url

    def __contains__(self, item):
        pass

    @property
    def specs(self) -> Mapping:
        pass

    @property
    def aliases(self) -> Mapping:
        pass

    def get_spec(
        self,
        identifier: str,
        flatten: bool,
        error_if_not_found: bool = True,
    ) -> Optional[Dict]:
        req_url = f"{self.root_api_url}/components/{identifier}/"
        response = requests.get(req_url)
        if not self._is_response_ok(response, error_if_not_found):
            return None
        data = json.loads(response.content)
        from pcs.component import Component  # Avoid circular import.

        flat_spec = {Component.IDENTIFIER_KEY: data[Component.IDENTIFIER_KEY]}
        flat_spec.update(data[self.SPEC_RESPONSE_BODY_KEY])
        return unflatten_spec(flat_spec) if not flatten else flat_spec

    def add_spec(self, spec: dict) -> None:
        """
        Handles HTTP request to backing webserver to upload a spec.
        Handles both nested and flat specs.
        """
        req_url = f"{self.root_api_url}/components/"
        flat_spec = spec if is_flat_spec(spec) else flatten_spec(spec)
        from pcs.component import Component  # Avoid circular import.

        identifier = flat_spec.pop(Component.IDENTIFIER_KEY)
        body = json.encoder.JSONEncoder().encode(flat_spec)
        data = {
            Component.IDENTIFIER_KEY: identifier,
            self.SPEC_RESPONSE_BODY_KEY: body,
        }
        logger.debug(f"\nabout to post spec http request: {data}")
        response = requests.post(req_url, data=data)
        self._is_response_ok(response)
        result = json.loads(response.content)
        logger.debug("\npost spec http response:")
        logger.debug(pprint.pformat(result))

    @staticmethod
    def _is_response_ok(
        response: requests.Response, error_if_not_found: bool = True
    ) -> bool:
        if response.ok:
            return True
        else:
            content = response.content
            try:
                content = json.loads(response.content)
                if type(content) == list:
                    content = content[0]
            except json.decoder.JSONDecodeError:
                try:
                    content.decode()
                except Exception:
                    pass
            if error_if_not_found:
                raise LookupError(response.text)
            else:
                return False

    def add_run_artifacts(
        self, run_id: int, run_artifact_paths: Sequence[str]
    ) -> Sequence:
        try:
            tmp_dir_path = Path(tempfile.mkdtemp())
            tar_gz_path = tmp_dir_path / f"run_{run_id}_artifacts.tar.gz"
            with tarfile.open(tar_gz_path, "w:gz") as tar:
                for artifact_path in run_artifact_paths:
                    tar.add(artifact_path, arcname=artifact_path.name)
            files = {"tarball": open(tar_gz_path, "rb")}
            url = f"{self.root_api_url}/runs/{run_id}/upload_artifact/"
            response = requests.post(url, files=files)
            result = json.loads(response.content)
            return result
        finally:
            shutil.rmtree(tmp_dir_path)

    def to_dict(self) -> Dict:
        raise Exception("to_dict() is not supported on WebRegistry.")

    def add_alias(self, alias: str, identifier: str) -> None:
        raise NotImplementedError
