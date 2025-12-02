from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

User = get_user_model()


class Application(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True, null=True)
    code = models.CharField(max_length=64, unique=True)
    url = models.URLField()

    class Meta:
        verbose_name = 'Приложение'
        verbose_name_plural = 'Приложения'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if not creating:
            return

        ApplicationAccessPermission = apps.get_model(
            'permissions', 'ApplicationAccessPermission'
        )

        executors_qs = User.objects.filter(role='executor')

        permissions = [
            ApplicationAccessPermission(
                user_id=executor.pk,
                application_id=self.pk,
            )
            for executor in executors_qs
        ]
        if permissions:
            with transaction.atomic():
                ApplicationAccessPermission.objects.bulk_create(
                    permissions,
                    ignore_conflicts=True,
                )


class OfficeSudTask(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает запуска"),
        (STATUS_RUNNING, "В процессе"),
        (STATUS_SUCCESS, "Завершено"),
        (STATUS_ERROR, "Ошибка"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='offices_sud_tasks',
    )
    batch_name = models.CharField(
        'Название проекта',
        max_length=255,
        blank=True,
    )
    excel_file = models.CharField(
        "Имя файла Excel",
        max_length=500,
    )
    batch_id = models.CharField(
        "Batch ID в БД",
        max_length=64,
        blank=True,
    )
    container_id = models.CharField(
        "ID контейнера Docker",
        max_length=64,
        blank=True,
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField('Создано', default=timezone.now)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    last_error = models.TextField('Последняя ошибка', blank=True, null=True)

    class Meta:
        verbose_name = 'Office.sud задача'
        verbose_name_plural = 'Office.sud задачи'
        ordering = ['-created_at',]

    def __str__(self):
        return f"{self.batch_name or self.batch_id or self.pk} ({self.get_status_display()})"
