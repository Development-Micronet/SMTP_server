from django.contrib import admin

from .models import Alias, AppPassword, Domain, Mailbox


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "dkim_selector", "active", "created_at")
    search_fields = ("name",)


@admin.register(Mailbox)
class MailboxAdmin(admin.ModelAdmin):
    list_display = ("address", "user", "quota_mb", "active", "created_at")
    list_filter = ("domain", "active")
    search_fields = ("local_part", "user__username")
    exclude = ("password_hash",)  # set via the create_mailbox command / API only


@admin.register(Alias)
class AliasAdmin(admin.ModelAdmin):
    list_display = ("__str__", "active")
    list_filter = ("domain",)


@admin.register(AppPassword)
class AppPasswordAdmin(admin.ModelAdmin):
    list_display = ("mailbox", "label", "created_at", "last_used_at")
    exclude = ("password_hash",)
