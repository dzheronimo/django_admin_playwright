from django.urls import path

from . import views

app_name = "browser_agent"

urlpatterns = [
    path("ping/", views.agent_ping, name="agent_ping"),
    path("next-command/", views.agent_next_command, name="agent_next_command"),
    path("command-result/", views.agent_report_result, name="agent_report_result"),
    # JSON-токен для расширения (по сессии пользователя)
    path("token/", views.agent_get_token, name="agent_get_token"),
    # HTML-страница с токеном (по желанию, для человека)
    path("token-page/", views.show_agent_token, name="show_agent_token"),
]
