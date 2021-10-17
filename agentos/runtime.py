"""Functions and classes used by the AOS runtime."""
from inspect import signature, Parameter
import json
from functools import partial
import subprocess
import os
import sys
import yaml
import click
from datetime import datetime
import importlib.util
from pathlib import Path
import configparser
import importlib


def run_component(
    component_spec_file,
    component_name,
    entry_point,
    params=None,
    param_file=None,
):
    """
    :param component_spec_file: file containing this component's specification.
    :param component_name: name of component to run.
    :param entry_point: name of function to call on component.
    :param params: dict of params for the entry point being run.
    :param param_file: YAML to load params from for entry point being run.
    """
    params = params or {}
    entry_point_params = params
    if params:
        # NOTES: we currently assume the params arg contains params for the
        # call to the component entry point. We don't currently support CLI
        # arguments for other component entry points besides the entry_point
        # currently being run (e.g., params for the init() function of a
        # descendent dependency of the component being run).
        fully_qualified_params = {component_name: {entry_point: params}}
    else:
        fully_qualified_params = {}
    if param_file:
        params_from_file = _load_parameters(param_file)
        if params_from_file:
            try:
                fully_qualified_params = _merge_settings_dicts(
                    params_from_file, fully_qualified_params
                )
                entry_point_params = fully_qualified_params[component_name][
                    entry_point
                ]
            except KeyError:
                pass

    extras = {
        "__agentos__": {
            "component_spec_file": component_spec_file,
            "component_name": component_name,
            "entry_point": entry_point,
            "fully_qualified_params": fully_qualified_params,
        }
    }

    component = load_component_from_file(
        component_spec_file, component_name, fully_qualified_params, extras
    )

    entry_point_fn = getattr(component, entry_point)
    entry_point_fn(**entry_point_params)


def load_component_from_file(spec_file, component_name, params, extras):
    """Loads component from a component spec file. This returns an instance
    of a python class as specified by the named agentOS component spec,
    having been set up with attributes that reference all of its dependencies
    as specified in the same component spec.

    :param spec_file: an AgentOS component spec file
    :param component_name: name of the component class instance to return.
        The spec_file provided must contain a component spec with this name.
    :param params: Parameters for entry point and __init__ functions.
    :param extras: Dictionary of attributes to be attached to all components.
    :returns: Instantiated component class.
    """
    spec_path = Path(spec_file)
    config = configparser.ConfigParser()
    config.read(spec_path)
    visited_components = {}
    component = _load_component(
        config, component_name, params, visited_components, extras
    )
    return component


def _load_component(
    config, component_name, params, visited_components, extras
):
    """Recursively load a component from a config instance.

    :param config: an instance of a parsed agentos.ini file.
    :param component_name: name of the component class instance to return.
        The spec_file provided must contain a component spec with this name.
    :param visited_components: Dict of all classes visited or instantiated
        in this recursive algorithm so far.
    :param extras: Dictionary of attributes to be attached to all components.

    :returns: Instantiated component class.
    """
    assert (
        component_name not in visited_components
    ), "AgentOS encountered a cycle in the component dependencies."
    visited_components[component_name] = None

    # if this component has dependencies, load them first (recursively)
    # Circular dependencies are not allowed.
    # then load an instance of this components class, and set up attributes
    # that point to the instances of its dependencies.
    dependencies = {}
    if "dependencies" in config[component_name].keys():
        dep_names = json.loads(config[component_name]["dependencies"])
        for dep_name in dep_names:
            if dep_name in visited_components:
                assert visited_components[dep_name]
                dep_obj = visited_components[dep_name]
            else:
                dep_obj = _load_component(
                    config, dep_name, params, visited_components, extras
                )
            dependencies[dep_name] = dep_obj
    component_class = _get_class_from_config_section(config[component_name])
    """
    For each component being loaded, AgentOS sets up an attribute for each
    of that component's dependencies. Then AgentOS calls the component's
    __init__() function, passing in any parameters specified by the user.
    To get this ordering correct AgentOS first initializes each component
    using a dummy empty __init__() function, then sets up its dependency
    attributes, then calls its true __init__() function.
    """
    component_class.__agentos_tmp_ini__ = component_class.__init__
    component_class.__init__ = lambda self: None
    component_instance = component_class()
    for dep_name, dep_obj in dependencies.items():
        setattr(component_instance, dep_name, dep_obj)
    component_class.__init__ = component_class.__agentos_tmp_ini__
    _call_component_func(
        component_name, component_instance, "__init__", params
    )
    for k, v in extras.items():
        setattr(component_instance, k, v)
    visited_components[component_name] = component_instance
    print(f"Loaded component {component_name}.")
    return component_instance


def _call_component_func(c_name, c_instance, func_name, params):
    assert hasattr(
        c_instance, func_name
    ), f"component {c_name} does not have a function named {func_name}."
    try:
        func_params = params[c_name][func_name]
    except KeyError:
        func_params = None
    if func_params is None:
        func_params = {}
    try:
        global_params = params["__global__"]
    except KeyError:
        global_params = None
    if global_params is None:
        global_params = {}
    merged_params = _merge_settings_dicts(global_params, func_params)
    partial_func = getattr(c_instance, func_name)
    sig = signature(partial_func)
    """
    look through all except the first param (first one was `self`):
      If param.type == POSITION_ONLY:
        error: agentos does now allow init() to have position-only args
      else if param.type is POSITION_OR_KEYWORD or KEYWORD_ONLY:
        assert this param.name is in the param dict provided by user
        new partial with param.name=user_params[param.name], and remove
            it from the user param dict
      else if it is type VAR_KEYWORD:
        # bind all remaining params from user param dict
        for user_param in user param dict:
          new partial with user_param call with user_param
      Note that we implicitly ignore the final case, i.e.,
      that the parm was of type VAR_POSITIONAL
      since all user specified params are named.
    """
    for param in sig.parameters.values():
        # AgentOS ignores arguments that it was of type VAR_POSITIONAL
        # since all user specified params are named.
        if param.kind == Parameter.POSITIONAL_ONLY:
            raise Exception(
                "AgentOS does not allow component entry points to "
                "accept position-only args."
            )
        elif param.kind in [
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
        ]:
            try:
                partial_func = partial(
                    partial_func,
                    **{param.name: merged_params.pop(param.name)},
                )
            except KeyError:
                f"Argument {param.name} required by {c_name}.{func_name}()"
                "but not found in provided parameters."
        elif param.kind == Parameter.VAR_KEYWORD:
            for p_name, p_val in merged_params.items():
                partial_func = partial(partial_func, **{p_name: p_val})
    try:
        partial_func()
    except Exception as e:
        # This helpful message hopefully makes debugging easier.
        print(
            f"\nThe AgentOS call to component initialization "
            f"{c_name}.{func_name}() failed."
        )
        raise e


def install_component(component_name, agentos_dir, agent_file, assume_yes):
    _check_path_exists(agentos_dir)
    agentos_dir = Path(agentos_dir).absolute()
    registry_entry = _get_registry_entry(component_name)
    confirmed = assume_yes or _confirm_component_installation(
        registry_entry, agentos_dir
    )
    if confirmed:
        # Blow away agent training step count
        agentos_dir.mkdir(exist_ok=True)
        release_entry = _get_release_entry(registry_entry)
        repo = _clone_component_repo(release_entry, agentos_dir)
        _checkout_release_hash(release_entry, repo)
        _update_agentos_ini(registry_entry, release_entry, repo, agent_file)
        _install_requirements(repo, release_entry)
    else:
        raise Exception("Aborting installation...")


def initialize_agent_directories(dir_names, agent_name, agentos_dir):
    dirs = [Path(".")]
    if dir_names:
        dirs = [Path(d) for d in dir_names]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        os.makedirs(agentos_dir, exist_ok=True)
        _instantiate_template_files(d, agent_name)
        d = "current working directory" if d == Path(".") else d
        click.echo(
            f"Finished initializing AgentOS agent '{agent_name}' in {d}."
        )


################################
# Private helper functions below
################################

# Modified from https://stackoverflow.com/a/7205107
def _merge_settings_dicts(a, b, path=None):
    """Merges dict b into dict a, overwriting duplicate keys in a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                _merge_settings_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]  # Keep differing value from b
        else:
            a[key] = b[key]
    return a


# Necessary because the agentos_dir will **not** exist on `agentos init`
def _check_path_exists(path):
    if not Path(path).absolute().exists():
        raise click.BadParameter(f"{path} does not exist!")


def _load_parameters(parameters_file) -> dict:
    with open(parameters_file) as file_in:
        params = yaml.full_load(file_in)
        assert isinstance(params, dict)
        return params


def _get_class_from_config_section(section):
    """Takes class_path of form "module.Class" and returns the class object."""
    module_file = Path(section["file_path"])
    assert module_file.is_file(), f"{module_file} is not a file"
    sys.path.append(str(module_file.parent))
    spec = importlib.util.spec_from_file_location(
        "TEMP_MODULE", str(module_file)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, section["class_name"])
    sys.path.pop()
    return cls


def _get_registry_entry(component_name):
    agentos_root_path = Path(__file__).parent.parent
    registry_path = agentos_root_path / "registry.yaml"
    if not registry_path.is_file():
        raise Exception(f"Could not find AgentOS registry at {registry_path}")
    with open(registry_path) as file_in:
        registry = yaml.full_load(file_in)
    if component_name not in registry:
        raise click.BadParameter(f'Cannot find component "{component_name}"')
    registry[component_name]["_name"] = component_name
    return registry[component_name]


def _confirm_component_installation(registry_entry, location):
    answer = input(
        f'ACR will install component {registry_entry["_name"]} '
        f"to {location}.  Continue? (Y/N) "
    )
    return answer.strip().lower() == "y"


def _get_release_entry(registry_entry):
    # TODO - allow specification of release
    return registry_entry["releases"][0]


def _clone_component_repo(release, location):
    repo_name = release["github_url"].split("/")[-1]
    clone_destination = (Path(location) / repo_name).absolute()
    if clone_destination.exists():
        raise click.BadParameter(f"{clone_destination} already exists!")
    cmd = ["git", "clone", release["github_url"], clone_destination]
    result = subprocess.run(cmd)
    assert result.returncode == 0, "Git returned non-zero on repo checkout"
    assert clone_destination.exists(), f"Unable to clone repo {repo_name}"
    return clone_destination


def _checkout_release_hash(release, repo):
    curr_dir = os.getcwd()
    os.chdir(repo)
    git_hash = release["hash"]
    cmd = ["git", "checkout", "-q", git_hash]
    result = subprocess.run(cmd)
    assert result.returncode == 0, f"FAILED: checkout {git_hash} in {repo}"
    os.chdir(curr_dir)


def _update_agentos_ini(registry_entry, release_entry, repo, agent_file):
    print(repo)
    config = configparser.ConfigParser()
    config.read(agent_file)
    if registry_entry["type"] == "environment":
        section = "Environment"
    elif registry_entry["type"] == "policy":
        section = "Policy"
    elif registry_entry["type"] == "dataset":
        section = "Dataset"
    elif registry_entry["type"] == "trainer":
        section = "Trainer"
    else:
        raise Exception(f"Component component type: {registry_entry['type']}")

    # TODO - allow multiple components of same type installed
    if section in config:
        print(
            f"Replacing current environment {dict(config[section])} "
            f'with {registry_entry["_name"]}'
        )
    module_path = Path(repo).absolute()
    file_path = (module_path / release_entry["file_path"]).absolute()
    config[section]["file_path"] = str(file_path)
    config[section]["class_name"] = release_entry["class_name"]
    config[section]["python_path"] = str(module_path)
    with open(agent_file, "w") as out_file:
        config.write(out_file)


# TODO - automatically install?
def _install_requirements(repo, release_entry):
    req_path = (repo / release_entry["requirements_path"]).absolute()
    print("\nInstall component requirements with the following command:")
    print(f"\n\tpip install -r {req_path}\n")


def _instantiate_template_files(d, agent_name):
    AOS_PATH = Path(__file__).parent
    for file_path in _INIT_FILES:
        with open(AOS_PATH / file_path, "r") as fin:
            with open(d / file_path.name, "w") as fout:
                print(file_path)
                content = fin.read()
                now = datetime.now().strftime("%b %d, %Y %H:%M:%S")
                header = (
                    "# This file was auto-generated by `agentos init` "
                    f"on {now}."
                )
                fout.write(
                    content.format(
                        agent_name=agent_name,
                        file_header=header,
                        abs_path=d.absolute(),
                        os_sep=os.sep,
                    )
                )


_AGENT_DEF_FILE = Path("./templates/agent.py")
_ENV_DEF_FILE = Path("./templates/environment.py")
_DATASET_DEF_FILE = Path("./templates/dataset.py")
_TRAINER_DEF_FILE = Path("./templates/trainer.py")
_POLICY_DEF_FILE = Path("./templates/policy.py")
_AGENT_INI_FILE = Path("./templates/agentos.ini")


_INIT_FILES = [
    _AGENT_DEF_FILE,
    _ENV_DEF_FILE,
    _POLICY_DEF_FILE,
    _DATASET_DEF_FILE,
    _TRAINER_DEF_FILE,
    _AGENT_INI_FILE,
]
