import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

import regex
from deepdiff import grep

AOS_ROOT = Path(__file__).parent.absolute()
AOS_GLOBAL_CONFIG_DIR = Path.home() / ".agentos"
AOS_GLOBAL_CACHE_DIR = AOS_GLOBAL_CONFIG_DIR / "cache"
AOS_GLOBAL_REQS_DIR = AOS_GLOBAL_CACHE_DIR / "requirements_cache"
AOS_GLOBAL_REPOS_DIR = AOS_GLOBAL_CACHE_DIR / "repos_cache"

IDENTIFIER_REF_PREFIX = "spec:"
HASH_REGEXES = ["^[a-fA-F0-9]{32}$", "^[a-fA-F0-9]{40}$", "^[a-fA-F0-9]{64}$"]


def is_spec_body(item: Any) -> bool:
    if not isinstance(item, Mapping):
        return False
    from pcs.component import Component  # Avoid circular import

    type_attr = item.get(Component.TYPE_KEY, None)
    import pcs

    return type_attr and hasattr(pcs, type_attr)


def is_identifier(token: Any) -> bool:
    is_id = False
    for rx in HASH_REGEXES:
        is_id = is_id or (regex.match(rx, str(token)) is not None)
    return is_id


def is_identifier_ref(token: Any) -> bool:
    return str(token).startswith(IDENTIFIER_REF_PREFIX)


def extract_identifier(identifier_ref: str) -> str:
    assert identifier_ref.startswith(IDENTIFIER_REF_PREFIX)
    prefix_len = len(IDENTIFIER_REF_PREFIX)
    return identifier_ref[prefix_len:]


def make_identifier_ref(identifier: str) -> str:
    return IDENTIFIER_REF_PREFIX + identifier


def parse_github_web_ui_url(
    github_url: str,
) -> (str, Optional[str], Optional[str]):
    """
    Parses a GitHub web UI URL pointing to a project root, of form::

        https://github.com/<project>/<repo>/

    or pointing to a specific file in a project, of form::

        https://github.com/<project>/<repo>/{blob,raw}/<branch>/<path>

    This will replace an SSH URL (i.e. one that starts with
    ``git@github.com:``) into a URL that starts with ``https://github.com/``.

    This returns a 4-tuple of:

    1. The GitHub project name

    2. The GitHub repo name

    3. The branch_name or commit hash contained in the URL (``None`` if URL is
       of the project root form)

    4. The path of the file contained in the suffix of the URL (``None`` if
       URL is of the project root form)
    """
    URL_STARTS_WITH = "https://github.com"
    # https repo link allows for cloning without unlocking your GitHub keys
    github_url = github_url.replace("git@github.com:", f"{URL_STARTS_WITH}/")
    error_msg = f'URL must start "{URL_STARTS_WITH}", not "{github_url}"'
    assert github_url.startswith(URL_STARTS_WITH), error_msg
    stripped_url = github_url.replace(f"{URL_STARTS_WITH}/", "", 1)
    split_url = stripped_url.split("/")
    assert len(split_url) >= 2, f" No project or repo in url: {github_url}"
    project_name = split_url[0]
    repo_name = split_url[1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    # Check if URL is just a link to a GitHub project root
    if len(split_url) == 2:
        return project_name, repo_name, None, None

    # If split is not *just* a project root, then it should look like
    # [<project>, <repo>, {blob/raw}, <branch>, <path_1>, <path_2>, ...]
    assert len(split_url) >= 5, f"Can't find required paths in: {github_url}"
    branch_name = split_url[3]
    repo_path = "/".join(split_url[4:])
    return project_name, repo_name, branch_name, repo_path


def clear_cache_path(cache_path: Path, assume_yes: bool):
    cache_path = Path(cache_path).absolute()
    if not cache_path.exists():
        print(f"Cache path {cache_path} does not exist.  Aborting...")
        return
    if assume_yes:
        answer = "y"
    else:
        answer = input(
            f"This will remove everything under {cache_path}. Continue? [Y/N] "
        )
    if assume_yes or answer.lower() in ["y", "yes"]:
        shutil.rmtree(cache_path)
        print("Cache cleared...")
        return
    print("Aborting...")


def nested_dict_list_replace(
    d: Dict, regex_str: str, replace_with: Any
) -> None:
    root = d
    results = root | grep(f"^{regex_str}$", use_regexp=True)
    if results:
        for dict_as_str in results["matched_values"]:
            # This is ugly and maybe unsafe and should be done in a more
            # sane way.
            assert isinstance(replace_with, str)
            exec(f"{dict_as_str} = '{replace_with}'")


def leaf_replace(data_struct: Any, leaf_list: List, replacement_fn: Callable):
    if not isinstance(data_struct, Dict) and not isinstance(data_struct, List):
        return
    next_inner = data_struct[leaf_list[0]]
    if isinstance(next_inner, Dict) or isinstance(next_inner, List):
        leaf_replace(next_inner, leaf_list[1:], replacement_fn)
    else:
        # This is the leaf we're looking for.
        assert len(leaf_list) == 2
        assert next_inner == leaf_list[-1]
        data_struct[leaf_list[0]] = replacement_fn(next_inner)


# From https://stackoverflow.com/a/12507546
def leaf_lists(data_struct: Any, pre: List = None):
    """
    Returns a list of lists, each inner list contains the sequence
    of keys necessary to index into data_struct to get to the leaf,
    followed by the value of the leaf itself.

    Example::

    >>> x = {1: [2, {3: 4}]}  # Has two leaves: 2 and 4.
    >>> [i for i in leaf_lists(x)]
    [[1, 0, 2], [1, 1, 3, 4]]
    """
    if not data_struct:
        return []
    pre = pre[:] if pre else []
    if isinstance(data_struct, dict):
        for key, value in data_struct.items():
            if isinstance(value, dict):
                yield from leaf_lists(value, pre + [key])
            elif isinstance(value, list) or isinstance(value, tuple):
                for i, v in enumerate(value):
                    yield from leaf_lists(v, pre + [key, i])
            else:
                yield pre + [key, value]
    elif isinstance(data_struct, list):
        for i, v in enumerate(data_struct):
            yield from leaf_lists(v, pre + [i])
    else:
        yield pre + [data_struct]


def filter_leaves(data_struct: Any, filter_fn: Callable) -> Dict:
    assert isinstance(data_struct, (list, dict)), (
        f"data_struct must be a list or dict, but is type "
        f"{type(data_struct)} (value: '{data_struct}')."
    )
    return {
        idx: leaf
        for *_, idx, leaf in leaf_lists(data_struct)
        if filter_fn(leaf)
    }


def find_and_replace_leaves(
    data_struct: Any, filter_fn: Callable, replace_fn: Callable
) -> bool:
    """
    :param data_struct: the list or dict to search
    :param filter_fn: the function to use when filtering
    :param replace_fn: a function that takes the existing leaf element
        and returns an element that will replace the existing one.
    :return: True if any matches were found
    """
    assert isinstance(data_struct, (list, dict)), (
        f"data_struct must be a list or dict, but is type "
        f"{type(data_struct)} (value: '{data_struct}')."
    )
    match_found = False
    for leaf_list in leaf_lists(data_struct):
        if filter_fn(leaf_list[-1]):
            leaf_replace(data_struct, leaf_list, replace_fn)
            match_found = True
    return match_found


def transform_leaf(
    orig_struct: Any,
    copy_struct: Any,
    leaf_list: List,
    replacement_fn: Callable,
):
    """
    Copy the leaf specified by ``leaf_list`` from orig_struct to
    copy_struct, applying replacement_fn.
    """
    if not isinstance(orig_struct, Dict) and not isinstance(orig_struct, List):
        return
    key, *remaining_keys = leaf_list
    next_inner = orig_struct[key]
    if isinstance(orig_struct, List):  # copy branch structure.
        assert isinstance(copy_struct, List)
        while key >= len(copy_struct):
            copy_struct.append(None)
        if copy_struct[key] is None:
            copy_struct[key] = {} if isinstance(next_inner, Dict) else []
    if isinstance(orig_struct, Dict):  # copy branch structure.
        assert isinstance(copy_struct, Dict)
        if key not in copy_struct:
            copy_struct[key] = {} if isinstance(next_inner, Dict) else []
    if isinstance(next_inner, Dict) or isinstance(next_inner, List):
        transform_leaf(
            next_inner, copy_struct[key], remaining_keys, replacement_fn
        )
    else:
        # This is the leaf we're looking for.
        assert len(leaf_list) == 2
        assert next_inner == leaf_list[-1]
        copy_struct[key] = replacement_fn(next_inner)


def copy_find_and_replace_leaves(
    data_struct: Any, filter_fn: Callable, replace_fn: Callable
) -> Tuple[bool, Union[List, Dict]]:
    """
    :param data_struct: the list or dict to copy and search
    :param filter_fn: the function to use when filtering
    :param replace_fn: a function that takes the existing leaf element
        and returns an element that will replace the existing one.
    :return: True if any matches were found, and the new structure reflecting
        the changes.
    """
    assert isinstance(data_struct, (List, Dict)), (
        f"data_struct must be a list or dict, but is type "
        f"{type(data_struct)} (value: '{data_struct}')."
    )
    copy_struct = {} if isinstance(data_struct, Dict) else []
    match_found = False
    for leaf_list in leaf_lists(data_struct):
        if filter_fn(leaf_list[-1]):
            transform_leaf(data_struct, copy_struct, leaf_list, replace_fn)
            match_found = True
        else:
            transform_leaf(data_struct, copy_struct, leaf_list, lambda x: x)
    return match_found, copy_struct


class spec_digraph:
    def __init__(self, init_dict: Dict):
        self._dict = {}  # a dict of Specs
        self.dependee_ids = defaultdict(set)
        self.dependency_ids = defaultdict(set)
        for ident, spec_body in init_dict.items():
            self.add(Spec({ident: spec_body}))

    def add_spec(self, spec: Spec):
        self._dict.update(spec)
        for _, spec_ref in filter_leaves(
                spec.body,
                lambda x: type(x) == str and IDENTIFIER_REF_PREFIX in x
        ).items():
            ref_id = extract_identifier(spec_ref)
            self.dependee_ids[ref_id].add(spec.identifier)
            self.dependency_ids[spec.identifier].add(ref_id)

    def pop_spec(self, identifier: str):

    def to_dict(self):
        return self._dict

