# Restore procedure (test this quarterly — an untested backup is a wish)

1. Provision a fresh host, install Docker, clone this repo, restore `.env`.
2. `restic restore latest --target /restore`
3. Start only postgres: `docker compose up -d postgres`
4. `cat /restore/.../mailstack-DATE.sql | docker compose exec -T postgres psql -U mailstack mailstack`
5. Copy Maildir back into the volume:
   `docker compose up -d dovecot` then
   `docker cp /restore/vmail/. $(docker compose ps -q dovecot):/var/vmail/ && docker compose exec dovecot chown -R vmail:vmail /var/vmail`
6. `docker compose up -d` — then rebuild the search index:
   `docker compose exec django python manage.py shell -c "from mail.tasks import index_all_mailboxes; index_all_mailboxes.delay()"`
7. Verify: IMAP login, webmail inbox renders, send + receive a round-trip test.
