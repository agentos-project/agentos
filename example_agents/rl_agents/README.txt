# Installing tensorflow on Apple Silicon

On 3/21/22, I created I got the dqn and reinforce agents in this directory
working on my first generation 13in Macbook Pro with the M1 chip (i.e.,
Apple Silicon).

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

