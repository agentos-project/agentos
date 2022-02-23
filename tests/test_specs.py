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
    assert "identifier" not in nested["local_dir"]
    assert "name" not in nested["local_dir"]
    assert "version" not in nested["local_dir"]

    # Test preserve identifier & parts when unflattening
    preserved_inner_id = unflatten_spec(
        flattened, preserve_inner_identifier=True
    )
    assert "local_dir" in preserved_inner_id.keys()
    assert preserved_inner_id["local_dir"]["type"] == "local"
    assert preserved_inner_id["local_dir"]["path"] == "."
    assert preserved_inner_id["local_dir"]["identifier"] == "local_dir"
    assert preserved_inner_id["local_dir"]["name"] == "local_dir"
    assert preserved_inner_id["local_dir"]["version"] is None

    # make sure we can go back and forth.
    re_flattened = flatten_spec(nested)
    assert re_flattened["type"] == "local"
    assert re_flattened["path"] == "."

    # make sure we used deepcopy for flatten and unflatten
    nested["local_dir"]["path"] = "new_path_val"
    assert flattened["path"] == "."
    flattened["path"] = "even_newer_path"
    assert nested["local_dir"]["path"] == "new_path_val"
    assert rand_repo_spec["local_dir"]["path"] == "."


def test_flatten_versioned_spec():
    reg = Registry.from_yaml(GH_SB3_AGENT_DIR / "components.yaml")
    rand_comp_spec = reg.get_component_spec("agent", "test_staging")
    full_comp_id = "agent==test_staging"
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
