from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

class MultiFieldAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        for field in ["username", "email", "phone_number"]:
            try:
                user = User.objects.get(**{field: username})
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                continue
        return None
