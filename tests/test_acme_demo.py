"""Test suite for Acme R2D2 Agent demo."""
import subprocess


# TODO - slow test; is there a way to speed this up?
# TODO - this needs an environment where dependencies are already installed
# TODO - is there a way to make this not depend on network?
def test_acme_r2d2_agent(tmpdir):
    try:
        import acme  # noqa: F401
    except ModuleNotFoundError:
        msg = (
            "This test must be run in an environment where all "
            'requirements are already installed.  Package "acme" not found.'
        )
        raise Exception(msg)
    subprocess.run(["agentos", "init", "."], cwd=tmpdir, check=True)
    subprocess.run(
        ["agentos", "install", "acme_r2d2_policy", "-y"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "install", "acme_r2d2_dataset", "-y"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "install", "acme_r2d2_trainer", "-y"],
        cwd=tmpdir,
        check=True,
    )
    subprocess.run(
        ["agentos", "install", "cartpole", "-y"], cwd=tmpdir, check=True
    )
    subprocess.run(["agentos", "run"], cwd=tmpdir, check=True)
    subprocess.run(["agentos", "learn"], cwd=tmpdir, check=True)
    subprocess.run(["agentos", "run"], cwd=tmpdir, check=True)
