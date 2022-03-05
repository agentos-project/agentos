from django.contrib import admin

from .models import Component, ComponentDependency, Repo, Run

admin.site.register(Component)
admin.site.register(ComponentDependency)
admin.site.register(Repo)
admin.site.register(Run)
