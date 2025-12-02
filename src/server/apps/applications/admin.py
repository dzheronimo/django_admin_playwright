from unfold.admin import ModelAdmin
from django.contrib import admin

from server.apps.applications.models import Application


@admin.register(Application)
class ApplicationAdmin(ModelAdmin):
    list_display = ('name', 'url')
    #TODO: При сохранении URL добавляется схема http:// (проверить что не критично)
