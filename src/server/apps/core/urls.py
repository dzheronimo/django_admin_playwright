from django.urls import path

from server.apps.core import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.user_logout, name='logout'),
]