from django.conf import settings
from django.db import models


class ApplicationAccessPermission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_access", verbose_name="Пользователь")
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='access_user', verbose_name='Приложение')
    is_access = models.BooleanField(default=False, verbose_name="Доступ")

    class Meta:
        verbose_name = "Доступ к приложению"
        verbose_name_plural = "Доступы к приложениям"
        unique_together = ('user', 'application')
