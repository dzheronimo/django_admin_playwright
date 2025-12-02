from django import forms
from django.apps import apps
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm

from server.apps.applications.models import Application


User = get_user_model()


class MultiFieldAdminLoginForm(AuthenticationForm):
    def get_user(self):
        return self.cleaned_data.get('user_cache')

    def normalize_phone(self, raw_phone):
        import re
        digits = re.sub(r'\D', '', raw_phone)
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        if digits.startswith('7'):
            return f'+{digits}'
        return raw_phone  # fallback

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        User = get_user_model()

        for field in ['username', 'email', 'phone_number']:
            value = username
            if field == 'phone_number':
                value = self.normalize_phone(username)
            try:
                user = User.objects.get(**{field: value})
                if user.check_password(password):
                    user.backend = 'server.apps.users.auth.MultiFieldAuthBackend'
                    self.confirm_login_allowed(user)
                    self.cleaned_data['user_cache'] = user
                    return self.cleaned_data
            except User.DoesNotExist:
                continue

        raise forms.ValidationError('Invalid username or password.')


class UserWithAppsForm(forms.ModelForm):
    """
    Форма пользователя с чекбоксами по приложениям
    """
    applications = forms.ModelMultipleChoiceField(
        queryset=Application.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Доступные приложения',
    )

    class Meta:
        model = User
        exclude = ('date_joined', 'last_login')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            ApplicationAccessPermission = apps.get_model(
                'permissions',
                'ApplicationAccessPermission'
            )
            allowed_apps_ids = ApplicationAccessPermission.objects.filter(
                user=self.instance,
                is_access=True,
            ).values_list('application_id', flat=True)
            self.fields['applications'].initial = Application.objects.filter(
                id__in=allowed_apps_ids,
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.save()
        ApplicationAccessPermission = apps.get_model(
            'permissions',
            'ApplicationAccessPermission'
        )

        selected_apps = list(self.cleaned_data.get('applications', []))
        all_apps = list(Application.objects.all())

        for app in all_apps:
            perm, created = ApplicationAccessPermission.objects.get_or_create(
                user=user,
                application=app,
                defaults={'is_access': False},
            )
            perm.is_access = app in selected_apps
            perm.save()

        return user
