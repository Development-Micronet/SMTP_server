from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('emails/', views.email_list, name='email_list'),
    path('emails/<int:pk>/', views.email_detail, name='email_detail'),
    path('emails/<int:pk>/delete/', views.email_delete, name='email_delete'),
    
    path('mailboxes/', views.mailbox_list, name='mailbox_list'),
    path('mailboxes/create/', views.mailbox_create, name='mailbox_create'),
    path('mailboxes/<int:pk>/delete/', views.mailbox_delete, name='mailbox_delete'),
    
    path('domains/', views.domain_list, name='domain_list'),
    path('domains/<int:pk>/delete/', views.domain_delete, name='domain_delete'),
    
    path('aliases/', views.alias_list, name='alias_list'),
    path('aliases/create/', views.alias_create, name='alias_create'),
    path('aliases/<int:pk>/delete/', views.alias_delete, name='alias_delete'),
]
