from typing import Dict, List

from django.db import models
from rest_framework.exceptions import ValidationError

from agentos.identifiers import ComponentIdentifier


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False)
    updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class ComponentDependency(TimeStampedModel):
    depender = models.ForeignKey(
        "Component", on_delete=models.CASCADE, related_name="depender_set"
    )
    dependee = models.ForeignKey(
        "Component", on_delete=models.CASCADE, related_name="dependee_set"
    )
    attribute_name = models.TextField()

    class Meta:
        unique_together = [("depender", "dependee", "attribute_name")]

    def __str__(self):
        return (
            f"<ComponentDependency {self.pk}: "
            f"{self.depender} depends on {self.dependee}>"
        )

    @staticmethod
    def create_from_dict(component_spec_dict: Dict) -> List:
        dependencies = []
        for name, component in component_spec_dict.items():
            identifier = ComponentIdentifier(name)
            depender = Component.objects.get(
                name=identifier.name,
                version=identifier.version,
            )
            for attr_name, dependency in component["dependencies"].items():
                dep_identifier = ComponentIdentifier(dependency)
                dependee = Component.objects.get(
                    name=dep_identifier.name,
                    version=dep_identifier.version,
                )
                dependency, create = ComponentDependency.objects.get_or_create(
                    depender=depender,
                    dependee=dependee,
                    attribute_name=attr_name,
                )
                dependencies.append(dependency)
        return dependencies


class Component(TimeStampedModel):
    identifier = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=200)
    repo = models.ForeignKey(
        "Repo",
        on_delete=models.CASCADE,
        related_name="repos",
        to_field="identifier",
    )
    file_path = models.TextField()
    class_name = models.CharField(max_length=200)
    instantiate = models.BooleanField()

    dependencies = models.ManyToManyField(
        "Component",
        through="ComponentDependency",
        through_fields=("depender", "dependee"),
    )

    class Meta:
        unique_together = [("name", "version")]

    def __str__(self):
        return f"<Component {self.pk}>"

    @property
    def short_version(self):
        display_version = self.version
        if len(display_version) == 40:
            display_version = display_version[:7]
        return display_version

    @property
    def full_name(self):
        return f"{self.name}=={self.version}"

    def top_five_runs(self):
        return (
            self.runs_as_environment.all()
            .distinct()
            .order_by("-mlflow_metrics__mean_reward")[:5]
        )

    def get_full_spec(self):
        repos = {}
        components = {}
        todo = [self]
        while len(todo) > 0:
            current = todo.pop()
            components[current.full_name] = current._to_spec()
            repos[current.repo.full_name] = current.repo._to_spec()
            for dependency in current.dependencies.all():
                todo.append(dependency)
        return {"repos": repos, "components": components}

    def _to_spec(self):
        dependencies = {}
        c_deps = ComponentDependency.objects.filter(depender=self).distinct()
        for c_dep in c_deps:
            dependencies[c_dep.attribute_name] = c_dep.dependee.full_name
        return {
            "repo": self.repo.full_name,
            "file_path": self.file_path,
            "class_name": self.class_name,
            "instantiate": self.instantiate,
            "dependencies": dependencies,
        }

    @staticmethod
    def create_from_flat_spec(flat_spec: Dict) -> List:
        identifier = ComponentIdentifier(flat_spec["identifier"])
        default_kwargs = {
            "name": identifier.name,
            "version": identifier.version,
            "repo": Repo.objects.get(identifier=flat_spec["repo"]),
            "file_path": flat_spec["file_path"],
            "class_name": flat_spec["class_name"],
            "instantiate": flat_spec.get("instantiate", False),
        }
        # TODO - When we have accounts, we need to check the the user
        #        has permission to create a new version of this Component
        #        (i.e. if the name already exists but not the version).
        component, created = Component.objects.get_or_create(
            identifier=identifier,
            defaults=default_kwargs,
        )
        # If not created and not equal, prevent Component redefinition
        if not created and not component._equals_spec(flat_spec):
            raise ValidationError(
                f"Component with id {identifier} already exists and "
                "differs from uploaded spec. Try renaming your Component."
            )
        return component

    # TODO - check versions in here once we have Component owners
    def _equals_spec(self, other_spec):
        other_repo = Repo.objects.get(identifier=other_spec["repo"])
        if self.repo.url != other_repo.url:
            return False
        if self.file_path != other_spec["file_path"]:
            return False
        if self.class_name != other_spec["class_name"]:
            return False
        if self.instantiate != other_spec["instantiate"]:
            return False
        self_deps = ComponentDependency.objects.filter(
            depender=self
        ).distinct()
        for self_dep in self_deps:
            if self_dep.attribute_name not in other_spec["dependencies"]:
                return False
            other_dep_name = other_spec["dependencies"][
                self_dep.attribute_name
            ]
            if other_dep_name != self_dep.dependee.full_name:
                return False
        return True


class Repo(TimeStampedModel):
    identifier = models.CharField(max_length=200, primary_key=True)
    type = models.CharField(max_length=200)
    url = models.CharField(max_length=200)

    def __str__(self):
        return f"<Repo '{self.identifier}' type {self.type} at {self.url}>"

    @staticmethod
    def create_from_dict(repo_spec_dict: Dict) -> List:
        repos = []
        for identifier, repo in repo_spec_dict.items():
            if "github.com" not in repo["url"]:
                raise ValidationError(
                    f"Repo must be on GitHub, not {repo['url']}"
                )
            repo, created = Repo.objects.get_or_create(
                identifier=identifier, url=repo["url"]
            )
            repos.append(repo)
        return repos

    @property
    def full_name(self):
        return f"{self.identifier}"

    def _to_spec(self):
        return {
            "type": "github",
            "url": self.url,
        }


class RunCommand(TimeStampedModel):
    identifier = models.CharField(max_length=200, primary_key=True)
    entry_point = models.CharField(max_length=200)
    argument_set = models.JSONField(default=dict)
    log_return_value = models.BooleanField()
    component = models.ForeignKey(
        Component, on_delete=models.CASCADE, to_field="identifier"
    )

    def __str__(self):
        return (
            f"identifier {self.identifier} with entry point "
            f"{self.entry_point}, argument_set {self.argument_set}, "
            f"and log_return_value {self.log_return_value}>"
        )


class Run(TimeStampedModel):
    identifier = models.CharField(max_length=200, primary_key=True)
    info = models.JSONField(default=dict)
    data = models.JSONField(default=dict)
    artifact_tarball = models.FileField(
        upload_to="artifact_tarballs/", null=True
    )
    run_command = models.ForeignKey(
        RunCommand, on_delete=models.CASCADE, null=True
    )
    agent = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        related_name="runs_as_agent",
        null=True,
    )
    environment = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        related_name="runs_as_environment",
        null=True,
    )

    def __str__(self):
        s = f"<Run {self.pk}"
        if self.run_command:
            s.append(f" with run_command '{self.run_command.identifier}'")
        if self.agent or self.environment:
            assert self.agent and self.environment
            s.append(
                f" with agent '{self.agent}' and environment "
                f"'{self.environment}'"
            )
        s.append(">")
        return s

    @property
    def training_step_count_metric(self):
        return self.mlflow_metrics.get("training_step_count", 0)

    @property
    def mean_reward_metric(self):
        return self.mlflow_metrics.get("mean_reward", 0)

    @property
    def display_string(self):
        return (
            f"Agent: {self.agent.name}, "
            f"Environment: {self.environment.name}, "
            f"Total Training Transitions: {self.training_step_count_metric}, "
            f"Mean Reward: {self.mean_reward_metric}"
        )
