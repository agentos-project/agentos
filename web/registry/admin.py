from django.contrib import admin

from .models import Component
from .models import ComponentDependency
from .models import Repo
from .models import Run

admin.site.register(Component)
admin.site.register(ComponentDependency)
admin.site.register(Repo)
admin.site.register(Run)
