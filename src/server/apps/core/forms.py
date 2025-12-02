import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Логин или телефон"),
        widget=forms.TextInput(attrs={"autofocus": True}),
    )

    error_messages = {
        "invalid_login": _(
            "Неверный логин/email/номер телефона или пароль. "
            "Проверьте введённые данные и попробуйте ещё раз."
        ),
        "inactive": _("Этот аккаунт отключён."),
    }

    def _normalize_username(self, value: str) -> str:
        if not value:
            return value

        raw = value.strip()

        digits = re.sub(r"\D+", "", raw)

        if len(digits) == 11 and digits[0] in {"7", "8"}:
            digits = "7" + digits[-10:]

        if len(digits) == 11 and digits.startswith("7"):
            return f"+{digits}"

        return value

    def clean(self):
        username = self.cleaned_data.get("username")

        if username:
            normalized = self._normalize_username(username)
            self.cleaned_data["username"] = normalized

        return super().clean()
