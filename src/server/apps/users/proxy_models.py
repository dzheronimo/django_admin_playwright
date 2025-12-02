from django.contrib.auth import get_user_model

User = get_user_model()

class AdminUserProxy(User):
    class Meta:
        proxy = True
        verbose_name = 'Администратор'
        verbose_name_plural = 'Администраторы'
