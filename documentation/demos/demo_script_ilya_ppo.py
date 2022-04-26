import pprint

from pcs.component import Module
from pcs.registry import Registry
from pcs.repo import Repo

ilya_repo = Repo.from_github("ikostrikov", "pytorch-a2c-ppo-acktr-gail")
ilya_reg = Registry.from_repo(ilya_repo)
print(pprint.pprint(ilya_reg.to_dict()))

main_mod_comp = Module.from_registry(
    ilya_reg, "module:a2c_ppo_acktr__model.py==master"
)
main_module = main_mod_comp.get_object()
dir(main_module)
main_module.main()

# An alternative
# main_mod_comp = Module.from_repo(
#    ilya_repo,
#    "ilya==41332b78dfb50321c29bade65f9d244387f68a60",
#    file_path="main.py",
#    requirements_path="requirements.txt",
# )
# assert main_mod_comp.get_object().__class__.__name__ == "module"
