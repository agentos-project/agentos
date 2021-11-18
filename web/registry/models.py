from django.db import models


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
    unique_together = ["depender", "dependee", "attribute_name"]

    def __str__(self):
        return (
            f"<ComponentDependency {self.pk}: "
            f"{self.depender} depends on {self.dependee}>"
        )


class Component(TimeStampedModel):
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=200)
    unique_together = ["name", "version"]
    repo = models.ForeignKey(
        "Repo", on_delete=models.CASCADE, related_name="repos"
    )
    file_path = models.TextField()
    class_name = models.CharField(max_length=200)
    description = models.TextField()

    dependencies = models.ManyToManyField(
        "Component",
        through="ComponentDependency",
        through_fields=("depender", "dependee"),
    )

    def __str__(self):
        display_version = self.version
        if len(display_version) == 40:
            display_version = display_version[:7]

        return f"<Component {self.pk}: {self.name}=={display_version}>"


class Repo(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    github_url = models.CharField(max_length=200)

    def __str__(self):
        return f"<Repo {self.pk}: " f'"{self.name}" at {self.github_url}>'


class Run(TimeStampedModel):
    components = models.ManyToManyField(Component, related_name="runs")
    benchmark_data = models.JSONField(default=dict)
    agent_data = models.JSONField(default=dict)
    tarball = models.FileField(upload_to="tarballs/", null=True)

    @property
    def agent(self):
        return self.components.get(component_type=Component.AGENT)

    @property
    def environment(self):
        return self.components.get(component_type=Component.ENVIRONMENT)

    @property
    def other_components(self):
        exclude = [Component.ENVIRONMENT, Component.AGENT]
        return self.components.exclude(component_type__in=exclude)

    @property
    def training_transitions(self):
        return self.benchmark_data["total_training_transitions"]

    @property
    def display_string(self):
        return (
            f"Agent: {self.agent.name}, "
            f"Environment: {self.environment.name}, "
            f"Total Training Transitions: {self.training_transitions}"
        )
