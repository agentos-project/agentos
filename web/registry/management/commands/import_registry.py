from django.core.management.base import BaseCommand
from registry.models import Component
from registry.models import ComponentRelease
import requests
import yaml

# {'2048':
#    {
#            'type': 'environment',
#            'agent_os_versions': ['0.0.7'],
#            'description': 'The 2048 tile sliding game',
#            'releases': [
#                {
#                    'name': '1.0.0',
#                    'hash': 'a0d0451eff8da9f239b94db1ba7804274452cf79',
#                    'github_url': 'https://github.com/nickjalbert/2048',
#                    'file_path': 'agentos_2048.py',
#                    'class_name': 'AgentOS2048',
#                    'requirements_path': 'requirements.txt'
#                }
#            ]
#        }


class Command(BaseCommand):
    help = "Imports a registry.yaml specified by a given URL"

    def add_arguments(self, parser):
        parser.add_argument(
            "registry_url",
            type=str,
            help="URL of registry.yaml file to import.",
        )

    def handle(self, *args, **options):
        registry_url = options["registry_url"]
        result = requests.get(registry_url)
        registry = yaml.load(result.text, Loader=yaml.SafeLoader)
        for component_name, data in registry.items():
            component_type = {
                "environment": Component.ENVIRONMENT,
                "policy": Component.POLICY,
                "agent": Component.AGENT,
                "dataset": Component.DATASET,
                "trainer": Component.TRAINER,
            }[data["type"]]
            component = Component(
                name=component_name,
                description=data["description"],
                component_type=component_type,
            )
            component.save()
            for release in data["releases"]:
                release = ComponentRelease(
                    component=component,
                    name=release["name"],
                    git_hash=release["hash"],
                    github_url=release["github_url"],
                    file_path=release["file_path"],
                    class_name=release["class_name"],
                    requirements_path=release["requirements_path"],
                )
                release.save()
