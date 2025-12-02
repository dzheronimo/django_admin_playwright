from django.urls import path
from server.apps.applications.views import start_officesud_batch, get_officesud_progress

app_name = "applications"

urlpatterns = [
    path("office-sud/start/", start_officesud_batch, name="office_sud_start"),
    path("office-sud/progress/<int:task_id>/", get_officesud_progress, name="office_sud_progress"),

]
