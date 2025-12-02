import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BrowserAgentKey(models.Model):
    """
    Ключ, который пользователь вводит в расширении.
    Один ключ — привязан к одному пользователю.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="browser_agent_key",
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.user} / {self.key}"

    @staticmethod
    def generate_key() -> str:
        return uuid.uuid4().hex


class BrowserCommand(models.Model):
    """
    Команда от сервера к расширению.

    type:
    - OPEN_URL
    - CLICK
    - FILL
    - UPLOAD_FILE
    и т.п.
    """
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent to client"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="browser_commands",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    result_text = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.user} / {self.type} / {self.status}"
