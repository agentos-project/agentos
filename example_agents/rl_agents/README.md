# Running example RL Agents

The agents in this directory are simple implementations of
popular RL algorithms. They can each be run directly as a python
script file via (assumes python version 3.x):

```
python dqn_agent.py
python radndom_nn_policy_agent.py
python reinforce_agent.py
```

# Installing Tensorflow on Apple silicon

Since these agents use Tensorflow, which (as of 3/21/22) is not currently
supported by the Tensorflow community on Apple Silicon, we have included the
following notes about how to install the Apple fork of Tensorflow which does
run on Apple silicon.

I got the dqn and reinforce agents in this directory
working on my first generation 13in Macbook Pro with the M1 chip (i.e.,
Apple silicon).

```
cd agentos # agentos repo version 0.1.0-alpha
curl -fLO https://github.com/apple/tensorflow_macos/releases/download/v0.1alpha3/tensorflow_macos-0.1alpha3.tar.gz
tar xvzf tensorflow_macos-0.1alpha3.tar.gz
conda env create --file=example_agents/rl_agents/environment.yaml -n agentos_dev_with_tf_py_3_8
conda activate agentos_dev_with_tf_py_3_8
conda install scipy grpcio
pip install --upgrade --force --no-dependencies https://github.com/apple/tensorflow_macos/releases/download/v0.1alpha3/tensorflow_macos-0.1a3-cp38-cp38-macosx_11_0_arm64.whl https://github.com/apple/tensorflow_macos/releases/download/v0.1alpha3/tensorflow_addons_macos-0.1a3-cp38-cp38-macosx_11_0_arm64.whl
pip install -e .
pip install -r example_agents/rl_agents/requirements.txt
```

