from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from server.apps.applications.models import Application
from server.apps.users.forms import MultiFieldAdminLoginForm, UserWithAppsForm
from server.apps.users.models import User
from server.apps.users.proxy_models import AdminUserProxy

admin.site.login_form = MultiFieldAdminLoginForm


class UserAdminMixin(ModelAdmin):
    list_display = (
        "username",
        "email",
        "full_name",
        "is_active",
    )
    list_editable = ("is_active",)

    fieldsets = (
        (None, {
            "fields": ("username", "email", "first_name",
                       "last_name", "middle_name", "telegram_id",
                       "phone_number", "role", "is_active", 'password'),
        }),
    )

    @admin.display(description="Пользователь")
    def full_name(self, obj):
        return obj.get_full_name()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("app_access__application")

    def delete_queryset(self, request, queryset):
        base_qs = queryset.model._default_manager.filter(
            pk__in=queryset.values_list("pk", flat=True).distinct()
        )
        super().delete_queryset(request, base_qs)


@admin.register(User)
class UserAdmin(UserAdminMixin):
    """Приложение - Пользователи"""
    list_display = UserAdminMixin.list_display + ("apps_card",)

    form = UserWithAppsForm

    fieldsets = UserAdminMixin.fieldsets + (
        ("Доступ к приложениям", {
            "fields": ("applications",),
        }),
    )

    def get_changeform_initial_data(self, request):
        """Автоматически подставляем роль 'admin' при создании через эту админку"""
        return {'role': 'executor'}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user_q = (Q(is_superuser=False) & Q(is_staff=False)) | Q(role="executor")
        return qs.filter(user_q).distinct()

    @admin.display(description="Доступы к приложениям")
    def apps_card(self, obj):
        """
        Рисуем блок как на скрине:
        Email: ...
        [x] Действия ЧСИ:
        [ ] Проверка Исков:
        ...
        """
        # все пермишены пользователя (ApplicationAccessPermission)
        perms = obj.app_access.all()
        perms_by_app_id = {p.application_id: p.is_access for p in perms}

        parts = []

        for app in Application.objects.all().order_by("id"):
            has_access = perms_by_app_id.get(app.id, False)
            checkbox_html = '<input type="checkbox" disabled {}>'.format(
                "checked" if has_access else ""
            )
            parts.append(
                '<div style="display:flex;align-items:center;gap:.4rem;'
                'margin:0.1rem 0;">'
                f"{checkbox_html}<span>{app.name}:</span>"
                "</div>"
            )

        return format_html("".join(parts))


@admin.register(AdminUserProxy)
class AdminUserAdmin(UserAdminMixin):
    """Приложение - Администраторы (прокси)"""
    form = UserWithAppsForm

    def get_changeform_initial_data(self, request):
        """Автоматически подставляем роль 'admin' при создании через эту админку"""
        return {'role': 'admin'}

    def save_model(self, request, obj, form, change):
        if obj.role == 'admin' and not (obj.is_staff or obj.is_superuser):
            obj.is_staff = True
            obj.is_superuser = True
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        admin_q = Q(is_superuser=True) | Q(is_staff=True) | Q(role="admin")
        return qs.filter(admin_q).distinct()