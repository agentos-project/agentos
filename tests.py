def test_random_agent_step():
    from agentos.agents import RandomAgent
    from gym.envs.classic_control import CartPoleEnv
    agent = RandomAgent(CartPoleEnv)
    done = agent.step()
    assert not done, "CartPole never finishes after one random step."


def test_run_random_agent():
    from agentos.agents import RandomAgent
    from agentos import run_agent
    from gym.envs.classic_control import CartPoleEnv
    run_agent(RandomAgent, CartPoleEnv)

def test_cli(tmpdir):
    import subprocess
    from pathlib import Path
    subprocess.Popen(["agentos", "init"], cwd=tmpdir).wait()
    main = Path(tmpdir) / "main.py"
    ml_project = Path(tmpdir) / "MLProject"
    conda_env = Path(tmpdir) / "conda_env.yaml"
    assert main.is_file()
    assert ml_project.is_file()
    assert conda_env.is_file()
    commands = [
        ["agentos", "run", "main.py"],
        ["agentos", "run", "main.py", "main.py"],
        ["agentos", "run", "agentos.agents.RandomAgent", "gym.envs.classic_control.CartPoleEnv"],
    ]
    for c in commands:
        p = subprocess.Popen(c, cwd=tmpdir)
        p.wait()
        assert p.returncode == 0

    # also test when main.py exists and MLProject file does not.
    ml_project.unlink()  # delete MLProject file.
    p = subprocess.Popen(["agentos", "run"], cwd=tmpdir)
    p.wait()
    assert p.returncode == 0

