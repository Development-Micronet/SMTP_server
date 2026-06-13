"""Provision a mailbox end to end:  manage.py create_mailbox alice@example.com 's3cret'"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Domain, Mailbox
from accounts.services import dovecot_hash


class Command(BaseCommand):
    help = "Create a Django user (if needed), domain (if needed) and a live mailbox."

    def add_arguments(self, parser):
        parser.add_argument("address")
        parser.add_argument("password")
        parser.add_argument("--quota-mb", type=int, default=2048)

    def handle(self, *args, **opts):
        address, password = opts["address"], opts["password"]
        if "@" not in address:
            raise CommandError("address must be local@domain")
        local, domain_name = address.rsplit("@", 1)

        domain, _ = Domain.objects.get_or_create(name=domain_name.lower())
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=address, defaults={"email": address}
        )
        if created:
            user.set_password(password)
            user.save()

        if Mailbox.objects.filter(domain=domain, local_part=local).exists():
            raise CommandError(f"{address} already exists")

        mb = Mailbox.objects.create(
            user=user,
            domain=domain,
            local_part=local.lower(),
            password_hash=dovecot_hash(password),
            quota_mb=opts["quota_mb"],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Created {mb.address}  (maildir {mb.maildir_path}, quota {mb.quota_mb} MB).\n"
            "Dovecot will create the Maildir on first delivery/login."
        ))
