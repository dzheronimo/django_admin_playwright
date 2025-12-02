from django.contrib import admin

from .models import BrowserAgentKey, BrowserCommand


@admin.register(BrowserAgentKey)
class BrowserAgentKeyAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "created_at")
    search_fields = ("user__username", "user__email", "key")
    readonly_fields = ("key", "created_at")

    def save_model(self, request, obj, form, change):
        if not obj.key:
            obj.key = BrowserAgentKey.generate_key()
        super().save_model(request, obj, form, change)


@admin.register(BrowserCommand)
class BrowserCommandAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "status", "created_at", "updated_at")
    list_filter = ("status", "type", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
