from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Component


def _get_link_from_id(serializer, view_name, obj_id):
    request = serializer.context.get("request")
    result = reverse(view_name, args=[obj_id], request=request)
    return result


class ComponentSerializer(serializers.ModelSerializer):
    identifier_link = serializers.SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            "identifier",
            "body",
        ]
