from rest_framework import serializers
from .models import Component


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = [
            "id",
            "name",
            "version",
            "repo",
            "file_path",
            "class_name",
            "description",
            "dependencies",
        ]
