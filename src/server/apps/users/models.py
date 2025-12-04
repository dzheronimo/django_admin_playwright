import re

from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models, transaction


class UserManager(BaseUserManager):
    def create_user(self, username = None, email = None, phone_number = None, password = None, **extra_fields):
        if not (username or email or phone_number):
            raise ValueError('Users must have either login or email or phone_number')

        user = self.model(
            username = username,
            email = email,
            phone_number = phone_number,
            **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(
            self,
            username = None,
            email = None,
            phone_number = None,
            password = None,
            **extra_fields
    ):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        return self.create_user(
            username = username,
            email = email,
            phone_number = phone_number,
            password=password,
            **extra_fields)

    def get_clients(self):
        return self.filter(role='client')

    def get_staff(self):
        return self.filter(is_staff=True)

    def get_admins(self):
        return self.filter(role='admin')

    def get_superusers(self):
        return self.filter(is_superuser=True)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('executor', 'Исполнитель'),
        ('admin', 'Администратор'),
    )

    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=12, unique=True, blank=True, null=True, verbose_name='Телефонный номер')

    first_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='Имя')
    last_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='Отчество')

    telegram_id = models.CharField(max_length=30, blank=True, null=True)

    role = models.CharField(choices=ROLE_CHOICES, max_length=20, default='executor', verbose_name='Роль')
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, verbose_name='Активный')

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'

    REQUIRED_FIELDS = ['email',]

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def normalize_phone_number(self):
        digits = re.sub(r'\D', '', str(self.phone_number or ''))
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        if not digits.startswith('7'):
            raise ValueError('Неверный формат номера телефона')
        return f'+{digits}'

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = self.normalize_phone_number()

        creating = self.pk is None
        previous_role = None
        if not creating:
            previous_role = (
                type(self).objects
                .filter(
                    pk=self.pk,
                )
                .values_list('role', flat=True)
                .first()
            )

        super().save(*args, **kwargs)

        if self.role == 'executor' and (creating or previous_role != 'executor'):

            Application = apps.get_model('applications', 'Application')
            ApplicationAccessPermission = apps.get_model('permissions', 'ApplicationAccessPermission')

            apps_qs  = Application.objects.all()
            permissions = [
                ApplicationAccessPermission(
                    user_id=self.pk,
                    application=app,
                )
                for app in apps_qs
            ]

            if permissions:
                with transaction.atomic():
                    ApplicationAccessPermission.objects.bulk_create(
                        permissions,
                        ignore_conflicts=True,
                    )

    def __str__(self):
        return self.username or self.email or self.phone_number or f"User #{self.pk}"

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"User #{self.pk} - имя и фамилия не указаны"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"

    def get_short_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name[0].upper()}"
