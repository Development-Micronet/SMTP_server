from django.urls import path

from . import views

urlpatterns = [
    path("folders/", views.FolderListView.as_view(), name="api-folders"),
    path("messages/", views.MessageListView.as_view(), name="api-messages"),
    path("messages/<str:folder>/<int:uid>/", views.MessageDetailView.as_view(), name="api-message"),
    path("send/", views.SendView.as_view(), name="api-send"),
]
