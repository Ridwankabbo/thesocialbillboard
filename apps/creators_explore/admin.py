from django.contrib import admin
from .models import Creator

from unfold.admin import ModelAdmin
# Register your models here.

# admin.site.register(Creator)

@admin.register(Creator)
class TaskAdmin(ModelAdmin):
    pass