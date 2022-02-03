from agentos.specs import flatten_spec, unflatten_spec
from agentos.registry import Registry
from tests.utils import RANDOM_AGENT_DIR, GH_SB3_AGENT_DIR


def test_flatten_spec():
    reg = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    rand_repo_spec = reg.get_repo_spec("local_dir")
    assert "local_dir" in rand_repo_spec.keys()
    assert rand_repo_spec["local_dir"]["type"] == "local"
    assert rand_repo_spec["local_dir"]["path"] == "."

    flattened = flatten_spec(rand_repo_spec)
    assert flattened["identifier"] == "local_dir"
    assert flattened["type"] == "local"
    assert flattened["path"] == "."
    assert flattened["name"] == "local_dir"
    assert flattened["version"] is None

    nested = unflatten_spec(flattened)
    assert "local_dir" in nested.keys()
    assert nested["local_dir"]["type"] == "local"
    assert nested["local_dir"]["path"] == "."

    # make sure we used deepcopy
    flattened["path"] = "updated_path"
    assert rand_repo_spec["local_dir"]["path"] == "."
    assert nested["local_dir"]["path"] == "."


def test_flatten_versioned_spec():
    reg = Registry.from_yaml(GH_SB3_AGENT_DIR / "components.yaml")
    rand_comp_spec = reg.get_component_spec("agent", "test_staging")
    full_comp_id = f"agent==test_staging"
    assert full_comp_id in rand_comp_spec.keys()
    assert rand_comp_spec[full_comp_id]["repo"] == "aos_github"

    flattened = flatten_spec(rand_comp_spec)
    assert flattened["identifier"] == full_comp_id
    assert flattened["name"] == "agent"
    assert flattened["version"] == "test_staging"

    nested = unflatten_spec(flattened)
    assert full_comp_id in nested.keys()
    assert "name" not in nested.keys()
    assert "name" not in nested.values()
    assert "version" not in nested.keys()
    assert "version" not in nested.values()

    # make sure we used deepcopy
    flattened["repo"] = "update_repo"
    assert rand_comp_spec[full_comp_id]["repo"] == "aos_github"
    assert nested[full_comp_id]["repo"] == "aos_github"
