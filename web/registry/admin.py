from django.contrib import admin

from .models import Component


class ComponentAdmin(admin.ModelAdmin):
    list_display = ("identifier", "component_type", "artifact_tarball")

    @admin.display(description="Component Type")
    def component_type(self, obj):
        return f"{obj.body.get('type', 'unknown')}"


admin.site.register(Component, ComponentAdmin)
