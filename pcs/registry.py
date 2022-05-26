import abc
import copy
import json
import logging
import os
import pprint
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Dict, Mapping, Optional, Sequence, Tuple

import requests
import yaml
from deepdiff import DeepDiff
from dotenv import load_dotenv

from pcs.specs import Spec, flatten_spec, is_flat_spec, unflatten_spec
from pcs.utils import (
    IDENTIFIER_REF_PREFIX,
    extract_identifier,
    is_identifier,
    is_spec_body,
    make_identifier_ref,
    nested_dict_list_replace,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pcs import Module
    from pcs.repo import Repo

# add USE_LOCAL_SERVER=True to .env to talk to local server
load_dotenv()

AOS_WEB_BASE_URL = "https://aos-web.herokuapp.com"
if os.getenv("USE_LOCAL_SERVER", False) == "True":
    AOS_WEB_BASE_URL = "http://localhost:8000"
AOS_WEB_API_EXTENSION = "/api/v1"

AOS_WEB_API_ROOT = f"{AOS_WEB_BASE_URL}{AOS_WEB_API_EXTENSION}"
DEFAULT_REG_FILE = "components.yaml"


class Registry(abc.ABC):
    @staticmethod
    def from_dict(input_dict: Dict) -> "Registry":
        return InMemoryRegistry(input_dict=input_dict)

    @staticmethod
    def from_yaml(file_path: str) -> "Registry":
        with open(file_path) as file_in:
            config = yaml.safe_load(file_in)
        reg = InMemoryRegistry(input_dict=config)
        updated_specs = []
        for spec_id, spec_body in reg.specs.items():
            if spec_body["type"] == "LocalRepo":
                p = PurePath(spec_body["path"])
                if not p.is_absolute():
                    abs_path = (Path(file_path).parent / p).resolve()
                    updated_spec = Spec.from_flat(copy.deepcopy(spec_body))
                    updated_spec.update_body({"path": str(abs_path)})
                    updated_specs.append((spec_id, updated_spec))
        for old_id, updated in updated_specs:
            reg.replace_spec(old_id, updated)
        return reg

    @classmethod
    def from_file_in_repo(
        cls, repo: "Repo", file_path: str, version: str, format: str = "yaml"
    ) -> "Registry":
        """
        Read in a registry file from a repo.

        :param repo: Repo to load registry file from.
        :param file_path: Path within Repo that registry is located, relative
            to the repo root.
        :param format: Optionally specify the format of the registry file.
        :return: a new Registry object.
        """
        assert (
            format == "yaml"
        ), "YAML is the only registry file format supported currently"
        return cls.from_yaml(repo.get_local_repo_dir(version) / file_path)

    @classmethod
    def from_repo_inferred(
        cls,
        repo: "Repo",
        version: str = None,
        py_file_suffixes: Tuple[str] = (".py", ".python"),
        requirements_file: str = "requirements.txt",
    ):
        from pcs.module_manager import Module  # Avoid circular ref.

        reg = InMemoryRegistry()
        # get list of python files in Repo
        py_files = set()
        for suff in py_file_suffixes:
            found = repo.get_local_repo_dir(version=version).rglob(f"*{suff}")
            py_files = py_files.union(set(found))
        # create and register module, class, and class instance components
        for f in py_files:
            relative_path = f.relative_to(
                repo.get_local_repo_dir(version=version)
            )
            mod_version = version if version else repo.default_version
            module_kwargs = {
                "repo": repo,
                "file_path": str(relative_path),
                "version": mod_version,
            }
            if repo.get_local_file_path(
                requirements_file, version=mod_version
            ).is_file():
                module_kwargs.update(
                    {"requirements_path": str(requirements_file)}
                )
            mod_component = Module(**module_kwargs)
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
            cls._default_registry = WebRegistry(AOS_WEB_API_ROOT)
        return cls._default_registry

    @abc.abstractmethod
    def to_dict(self) -> Dict:
        raise NotImplementedError

    def to_yaml(self, filename: str = None) -> None:
        if filename:
            with open(filename, "w") as file:
                yaml.dump(self.to_dict(), file)
        else:
            return yaml.dump(self.to_dict())

    @property
    @abc.abstractmethod
    def specs(self) -> Mapping:
        raise NotImplementedError

    @property
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
                f"in this registry {self}"
            )
        else:
            return None
        spec = Spec.from_flat(body)
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
            self.add_alias(alias, i)

    def replace_spec(self, identifier, new_spec):
        replacements_to_do = [(identifier, new_spec)]
        while replacements_to_do:
            ident_to_replace, new_spec = replacements_to_do.pop()
            self.add_spec(new_spec)
            for ident, spec_body in self.specs.items():
                spec_copy = Spec.from_flat(spec_body)  # Makes deepcopy
                found = spec_copy.replace_in_body(
                    lambda x: x == make_identifier_ref(ident_to_replace),
                    lambda x: make_identifier_ref(new_spec.identifier),
                )
                if found:
                    replacements_to_do.append((ident, spec_copy))
            aliases_to_update = [
                alias
                for alias, ident in self.aliases.items()
                if ident == ident_to_replace
            ]
            for alias in aliases_to_update:
                self.aliases[alias] = new_spec.identifier


class InMemoryRegistry(Registry):
    """
    A mutable in-memory registry.
    """

    SPECS_KEY = "specs"
    ALIASES_KEY = "aliases"

    def __init__(self, input_dict: Dict = None):
        self._registry = {self.SPECS_KEY: {}, self.ALIASES_KEY: {}}
        if input_dict:
            for key in input_dict.keys():
                assert key == self.SPECS_KEY or key == self.ALIASES_KEY, (
                    f"'input_dict' can not have top level level keys besides "
                    f"'{self.SPECS_KEY}' and '{self.ALIASES_KEY}', but this "
                    f"has '{key}'."
                )
            self._registry.update(input_dict)
            self._resolve_inline_specs()
            self._resolve_aliases()

    @property
    def specs(self) -> Mapping:
        return self._registry[self.SPECS_KEY]

    @property
    def aliases(self) -> Mapping:
        return self._registry.get(self.ALIASES_KEY, {})

    # TODO: This function probably belongs in the Registry class.
    def _resolve_inline_specs(self):
        """
        Allow developers to specify specs in-line. This will rewrite those
        in a more normalized form. So, for example, resolve the following::

            specs:
                c6af7bc9d07271dfe75429ac8ee34398dfdc4338:
                    nested_spec1:  # nested spec
                        type: ComponentType1
                        nested_spec2:  # nested spec
                            type: ComponentType2
                            key2: val2
                    non_spec_dict:
                        - nested_spec3:  # nested spec
                            type: ComponentType3
                            key3: val3
                        - "a string"

        ...into::

            specs:
                c6af7bc9d07271dfe75429ac8ee34398dfdc4338:
                    nested_spec1: 271dfe754c6af7bc9d0729adfdc4338c8ee34398
                    non_spec_dict:
                        - 64d0729adf2e75caf7bc971d4398dc43cf883e3e
                        - "a string"

                271dfe754c6af7bc9d0729adfdc4338c8ee34398:
                    type: ComponentType1
                    nested_spec2: e75caf7bc964d0729adf271df838ee34398dc43c

                e75caf7bc964d0729adf271df838ee34398dc43c:
                    type: ComponentType2
                    key2: val2

                64d0729adf2e75caf7bc971d4398dc43cf883e3e:
                    type: ComponentType3
                    key3: val3

        """
        new_specs = {}
        to_handle = []
        for ident, body in self.specs.items():
            new_specs[ident] = {}
            to_handle += [(new_specs, ident, {k: v}) for k, v in body.items()]
        while to_handle:
            struct, key, elt = to_handle.pop()
            if elt and isinstance(elt, dict):  # handling dict
                for attr_key, attr_val in elt.items():
                    if is_spec_body(attr_val):  # normalize nested_spec
                        inner_spec = attr_val
                        from pcs.component import Component

                        inner_id = Component.spec_body_to_identifier(
                            inner_spec
                        )
                        struct[key][attr_key] = make_identifier_ref(inner_id)
                        new_specs[inner_id] = {}
                        to_handle.append((new_specs, inner_id, inner_spec))
                    else:
                        try:
                            struct[key]
                        except (IndexError, KeyError):
                            struct[key] = {}
                        to_handle.append((struct[key], attr_key, attr_val))
            elif elt and isinstance(elt, list):  # handling list
                try:
                    struct[key]
                except (IndexError, KeyError):
                    struct[key] = []
                for i, sub_elt in enumerate(elt):
                    to_handle.append((struct[key], i, sub_elt))
            else:  # elt must be leaf
                struct[key] = elt

        self._registry[self.SPECS_KEY] = new_specs

    # TODO: This function probably belongs in the Registry class.
    def _resolve_aliases(self):
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
        for id_or_alias, body in self.specs.items():
            assert is_spec_body(body), (
                "Trying to resolve aliases in something that is not spec "
                f"body: {body}"
            )
            from pcs.component import Component  # Avoid circular import.

            hash = Component.spec_body_to_identifier(body)
            if is_identifier(id_or_alias):
                new_specs[id_or_alias] = body
            else:
                if id_or_alias in new_aliases:
                    assert new_aliases[id_or_alias] == hash
                else:
                    new_aliases[id_or_alias] = hash
                new_specs[hash] = body
        # replace uses of aliases within the body of the spec.
        for alias in new_aliases.keys():
            for spec in new_specs:
                print(
                    f"replace '{alias}' with {new_aliases[alias]}, in spec: "
                    f"{spec}"
                )
                nested_dict_list_replace(
                    new_specs,
                    f"^{make_identifier_ref(alias)}$",
                    make_identifier_ref(new_aliases[alias]),
                )
        self._registry[self.SPECS_KEY] = new_specs
        if new_aliases:
            self._registry[self.ALIASES_KEY] = new_aliases

    def add_spec(self, spec: Dict) -> None:
        from pcs.component import Component  # Avoid circular import.

        flat_spec = flatten_spec(spec)
        identifier = flat_spec[Component.IDENTIFIER_KEY]
        if identifier in self.specs:
            spec_diff = DeepDiff(spec[identifier], self.specs[identifier])
            assert not spec_diff, (
                f"Spec {identifier} exists in registry and is different:\n\n"
                f"{spec_diff}"
            )
            print(f"Spec {identifier} is already in registry; nothing to do.")
        self._registry[self.SPECS_KEY].update(spec)

    def add_alias(self, alias: str, identifier: str) -> None:
        self._registry[self.ALIASES_KEY][alias] = identifier

    def to_dict(self) -> Dict:
        return self._registry


class WebSpecMapping(Mapping):
    def __init__(self, root_api_url: str):
        self.root_api_url = root_api_url

    def __getitem__(self, item):
        pass

    def __iter__(self):
        pass

    def __len__(self):
        req_url = f"{self.root_api_url}/components/"


class WebRegistry(Registry):
    """
    A web-server backed Registry.
    """

    SPEC_RESPONSE_BODY_KEY = "body"

    def __init__(self, root_api_url: str):
        self.root_api_url = root_api_url
        self.spec_mapping = WebSpecMapping(root_api_url)

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
        logger.debug(f"\npost spec http response:")
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
