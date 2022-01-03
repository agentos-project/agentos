from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import Run
from .models import Repo
from .models import Component


def _get_link_from_id(serializer, view_name, obj_id):
    request = serializer.context.get("request")
    result = reverse(view_name, args=[obj_id], request=request)
    return result


class ComponentSerializer(serializers.ModelSerializer):
    id_link = serializers.SerializerMethodField()
    repo_link = serializers.SerializerMethodField()
    github_source_link = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            "id",
            "id_link",
            "name",
            "version",
            "repo",
            "repo_link",
            "file_path",
            "class_name",
            "description",
            "dependencies",
            "github_source_link",
        ]

    def get_id_link(self, obj):
        return _get_link_from_id(self, "component-detail", obj.id)

    def get_repo_link(self, obj):
        return _get_link_from_id(self, "repo-detail", obj.repo.id)

    def get_github_source_link(self, obj):
        github_url = obj.repo.github_url
        if github_url.endswith(".git"):
            github_url = github_url[:-4]
        final_url = f"{github_url}/tree/{obj.version}/{obj.file_path}"
        return final_url


class RunSerializer(serializers.ModelSerializer):
    id_link = serializers.SerializerMethodField()
    root_link = serializers.SerializerMethodField()
    agent_link = serializers.SerializerMethodField()
    environment_link = serializers.SerializerMethodField()
    download_artifact_tarball_link = serializers.SerializerMethodField()
    root_spec_link = serializers.SerializerMethodField()

    class Meta:
        model = Run
        fields = [
            "id",
            "id_link",
            "root",
            "root_link",
            "agent",
            "agent_link",
            "environment",
            "environment_link",
            "mlflow_metrics",
            "mlflow_params",
            "mlflow_tags",
            "mlflow_info",
            "download_artifact_tarball_link",
            "root_spec_link",
            "entry_point",
            "parameter_set",
        ]

    def get_id_link(self, obj):
        return _get_link_from_id(self, "run-detail", obj.id)

    def get_root_link(self, obj):
        return _get_link_from_id(self, "component-detail", obj.root.id)

    def get_agent_link(self, obj):
        return _get_link_from_id(self, "component-detail", obj.agent.id)

    def get_environment_link(self, obj):
        return _get_link_from_id(self, "component-detail", obj.environment.id)

    def get_download_artifact_tarball_link(self, obj):
        return _get_link_from_id(self, "run-download-artifact", obj.id)

    def get_root_spec_link(self, obj):
        return _get_link_from_id(self, "run-root-spec", obj.id)


class RepoSerializer(serializers.ModelSerializer):
    id_link = serializers.SerializerMethodField()

    class Meta:
        model = Repo
        fields = [
            "id",
            "id_link",
            "name",
            "github_url",
        ]

    def get_id_link(self, obj):
        return _get_link_from_id(self, "repo-detail", obj.id)
