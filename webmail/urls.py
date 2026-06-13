from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="webmail/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.inbox, name="inbox"),
    path("folder/<str:folder>/", views.inbox, name="folder"),
    path("message/<str:folder>/<int:uid>/", views.message_detail, name="message"),
    path("message/<str:folder>/<int:uid>/delete/", views.message_delete, name="message_delete"),
    path("compose/", views.compose, name="compose"),
    path("search/", views.search, name="search"),
]
