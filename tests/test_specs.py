from pcs.registry import Registry
from pcs.specs import flatten_spec, unflatten_spec
from tests.utils import GH_SB3_AGENT_DIR, RANDOM_AGENT_DIR


def test_flatten_spec():
    reg = Registry.from_yaml(RANDOM_AGENT_DIR / "components.yaml")
    rand_repo_spec = reg.get_spec("local_dir")
    ident = rand_repo_spec.identifier
    assert rand_repo_spec[ident]["type"] == "LocalRepo"
    assert rand_repo_spec[ident]["path"] == str(RANDOM_AGENT_DIR)

    flattened = flatten_spec(rand_repo_spec)
    assert flattened["type"] == "LocalRepo"
    assert flattened["path"] == str(RANDOM_AGENT_DIR)

    nested = unflatten_spec(flattened)
    assert nested[ident]["type"] == "LocalRepo"
    assert nested[ident]["path"] == str(RANDOM_AGENT_DIR)
    assert "identifier" not in nested[ident]

    # make sure we can go back and forth.
    re_flattened = flatten_spec(nested)
    assert re_flattened["type"] == "LocalRepo"
    assert re_flattened["path"] == str(RANDOM_AGENT_DIR)

    # make sure we used deepcopy for flatten and unflatten
    nested[ident]["path"] = "new_path_val"
    assert flattened["path"] == str(RANDOM_AGENT_DIR)
    flattened["path"] = "even_newer_path"
    assert nested[ident]["path"] == "new_path_val"
    assert rand_repo_spec[ident]["path"] == str(RANDOM_AGENT_DIR)
