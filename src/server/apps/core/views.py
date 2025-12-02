from typing import Any

from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect

from server.apps.core.forms import UserLoginForm
from server.apps.permissions.models import ApplicationAccessPermission


def index(request):
    if request.method == "GET":
        user = request.user
        context: dict[str | Any] = {}
        if user.is_authenticated:
            context['user'] = user
            apps_access = (
                ApplicationAccessPermission.objects
                .filter(user=request.user)
                .exclude(is_access=False)
                .select_related('application'))
            context['apps'] = apps_access


        return render(request, 'index.html', context)


class UserLoginView(LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True
    authentication_form = UserLoginForm

def user_logout(request):
    logout(request)
    return redirect("index")