from unfold.admin import ModelAdmin

from django.contrib import admin

from server.apps.permissions.models import ApplicationAccessPermission


@admin.register(ApplicationAccessPermission)
class ApplicationAdmin(ModelAdmin):
    list_display = ('user_email', 'app_name', 'is_access')

    @admin.display(description="Email", ordering='user__email')
    def user_email(self, obj):
        return obj.user.email if obj.user else None

    @admin.display(description='Приложение', ordering='application__name')
    def app_name(self, obj):
        return obj.application.name if obj.application else None

