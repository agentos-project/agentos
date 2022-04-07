from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Component, ComponentDependency, Repo, Run, RunCommand


def _get_link_from_id(serializer, view_name, obj_id):
    request = serializer.context.get("request")
    result = reverse(view_name, args=[obj_id], request=request)
    return result


class RepoSerializer(serializers.ModelSerializer):
    identifier_link = serializers.SerializerMethodField()

    class Meta:
        model = Repo
        fields = [
            "identifier_link",
            "identifier",
            "type",
            "url",
        ]

    def get_identifier_link(self, obj):
        return _get_link_from_id(self, "repo-detail", obj.identifier)


class ComponentDependencySerializer(serializers.ModelSerializer):
    dependee_link = serializers.SerializerMethodField()

    class Meta:
        model = ComponentDependency
        fields = [
            "dependee",
            "dependee_link",
            "attribute_name",
        ]

    def get_dependee_link(self, obj):
        return _get_link_from_id(
            self, "component-detail", obj.dependee.identifier
        )


class ComponentSerializer(serializers.ModelSerializer):
    identifier_link = serializers.SerializerMethodField()
    repo_link = serializers.SerializerMethodField()
    github_source_link = serializers.SerializerMethodField()
    depender_set = ComponentDependencySerializer(many=True, read_only=True)

    class Meta:
        model = Component
        fields = [
            "identifier",
            "identifier_link",
            "name",
            "version",
            "repo",
            "repo_link",
            "file_path",
            "class_name",
            "instantiate",
            "depender_set",
            "github_source_link",
        ]

    def get_identifier_link(self, obj):
        return _get_link_from_id(self, "component-detail", obj.identifier)

    def get_repo_link(self, obj):
        return _get_link_from_id(self, "repo-detail", obj.repo.identifier)

    def get_github_source_link(self, obj):
        url = obj.repo.url
        if url.endswith(".git"):
            url = url[:-4]
        final_url = f"{url}/tree/{obj.version}/{obj.file_path}"
        return final_url


class RunCommandSerializer(serializers.ModelSerializer):
    identifier_link = serializers.SerializerMethodField()
    component_link = serializers.SerializerMethodField()

    class Meta:
        model = RunCommand
        fields = [
            "identifier",
            "identifier_link",
            "component",
            "component_link",
            "entry_point",
            "argument_set",
            "log_return_value",
        ]

    def get_identifier_link(self, obj):
        return _get_link_from_id(self, "runcommand-detail", obj.identifier)

    def get_component_link(self, obj):
        return _get_link_from_id(
            self, "component-detail", obj.component.identifier
        )


class RunSerializer(serializers.ModelSerializer):
    identifier_link = serializers.SerializerMethodField()
    download_artifact_tarball_link = serializers.SerializerMethodField()
    run_command_link = serializers.SerializerMethodField()
    agent_link = serializers.SerializerMethodField()
    environment_link = serializers.SerializerMethodField()

    class Meta:
        model = Run
        fields = [
            "identifier",
            "identifier_link",
            "info",
            "data",
            "download_artifact_tarball_link",
            "run_command",
            "run_command_link",
            "agent",
            "agent_link",
            "environment",
            "environment_link",
        ]

    def get_identifier_link(self, obj):
        return _get_link_from_id(self, "run-detail", obj.identifier)

    def get_run_command_link(self, obj):
        return _get_link_from_id(
            self, "runcommand-detail", obj.run_command.identifier
        )

    def get_download_artifact_tarball_link(self, obj):
        return _get_link_from_id(self, "run-download-artifact", obj.identifier)

    def get_agent_link(self, obj):
        if obj.agent:
            return _get_link_from_id(
                self, "component-detail", obj.agent.identifier
            )

    def get_environment_link(self, obj):
        if obj.environment:
            return _get_link_from_id(
                self, "component-detail", obj.environment.identifier
            )
