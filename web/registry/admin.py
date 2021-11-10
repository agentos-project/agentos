from django.contrib import admin

from .models import Component
from .models import ComponentRelease
from .models import Run

admin.site.register(Component)
admin.site.register(ComponentRelease)
admin.site.register(Run)
