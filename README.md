# MailStack

Self-hosted mail platform: **Django** control plane + webmail, **Postfix** (SMTP),
**Dovecot** (IMAP/Maildir), **rspamd** (spam + DKIM), **PostgreSQL**, **Redis/Celery**.

Postfix and Dovecot read users, domains and aliases **directly from Django's
database** via read-only SQL maps — provisioning a mailbox in Django makes the
address live instantly, with no config reloads.

```
Internet ──25──▶ Postfix (postscreen, rspamd milter) ──LMTP──▶ Dovecot ──▶ Maildir
User MUA ──993─────────────────────────────────────────────────▶ Dovecot
Browser ──443──▶ Nginx ──▶ Django webmail/API ──IMAP(master user)──▶ Dovecot
Outbound ──587 submission (SASL via Dovecot, DKIM-signed by rspamd)──▶ world
                 Celery ◀── Redis        PostgreSQL ◀── SQL lookups (Postfix/Dovecot)
```

## Quickstart

```bash
cp .env.example .env           # edit EVERYTHING marked CHANGEME
make up                        # build + start the stack
make migrate
make superuser                 # Django admin login
make adduser ADDR=alice@example.com PASS='a-long-passphrase'
```

Before real mail flows, complete **ops/dns-checklist.md** (A/PTR/MX/SPF/DKIM/DMARC)
and obtain certificates:

```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d mail.example.com --cert-name mail
```

Generate the DKIM key and publish the printed TXT record:

```bash
docker compose exec rspamd rspamadm dkim_keygen -d example.com -s mail \
  -k /var/lib/rspamd/dkim/example.com.mail.key
```

Then: log in to the webmail at `https://mail.example.com/`, or point any IMAP
client at port 993 / SMTP submission at 587.

## Layout

| Path | What |
|---|---|
| `config/` | Django settings, Celery app |
| `accounts/` | Domain / Mailbox / Alias / AppPassword models; `create_mailbox` command; Argon2 hashing shared with Dovecot |
| `mail/` | Message metadata index, IMAP layer (Dovecot master user), SMTP submission layer, Celery indexer |
| `webmail/` | HTMX-ready Django templates: inbox, read, compose, search |
| `api/` | DRF endpoints: folders, messages, message detail, send |
| `compose/postfix/` | main.cf, master.cf, PostgreSQL lookup maps |
| `compose/dovecot/` | dovecot.conf, SQL passdb/userdb, master-user setup |
| `compose/rspamd/` | DKIM signing, Bayes-in-Redis, milter headers |
| `compose/nginx/` | TLS termination, security headers, static files |
| `ops/` | backup/restore scripts, DNS & deliverability checklist |
| `tests/` | pytest unit tests (IMAP/SMTP mocked) |

## Design decisions

- **Don't reimplement SMTP/IMAP.** Postfix/Dovecot are battle-hardened; Django
  is the control plane and UI. The webmail talks to Dovecot over IMAP using the
  *master user* mechanism, so Django holds one service credential and never the
  user's password.
- **Maildir is the source of truth.** `mail.MessageMeta` is a rebuildable index
  for fast listing and Postgres full-text search.
- **One password, three doors.** Mailbox passwords are Argon2id hashes readable
  by Dovecot (`{ARGON2ID}` scheme), used for IMAP, SMTP submission SASL, and
  verifiable from Python. With 2FA enabled, IMAP clients use per-device
  `AppPassword`s instead.
- **Plain-text rendering only** in the webmail for now. Rendering HTML mail
  safely requires sanitization (nh3/bleach) + strict CSP — wire that up
  deliberately, not by default.

## Security checklist (already wired)

- TLS required on 587/993, opportunistic on 25; HSTS + CSP on the web tier
- SASL only on submission, never on port 25; sender must match login
- postscreen + Spamhaus DNSBL + rate limits on inbound; per-client rate limit on submission
- rspamd scoring inbound, DKIM signing outbound, Bayes autolearn from Junk
- Read-only SQL role for the MTA lookups; secrets only via `.env`
- Argon2id everywhere; 12-char minimum passwords; DRF throttling on the API

Still on you: encrypted disks/volumes for at-rest encryption, fail2ban on the
host, off-site `RESTIC_REPOSITORY`, and quarterly restore drills (`ops/restore.md`).

## Roadmap

- **M1 (this scaffold):** provisioning, send/receive, webmail inbox/read/compose/delete, search index
- **M2:** folder management UI, attachment download, Sieve rules UI, junk-folder Bayes training, quotas surfaced in UI
- **M3:** Prometheus exporters + Grafana, MTA-STS/TLS-RPT, DMARC report ingestion, smarthost failover
- **M4:** 2FA (django-otp) + app-password enforcement, shared mailboxes (Dovecot ACL), admin analytics, OIDC SSO

## First-run smoke test

```bash
make adduser ADDR=alice@example.com PASS='passphrase-one!'
make adduser ADDR=bob@example.com   PASS='passphrase-two!'
swaks --to bob@example.com --from alice@example.com \
      --server localhost:587 --tls -au alice@example.com -ap 'passphrase-one!'
# then log in as bob in the webmail — the message appears after the next
# index run (≤5 min) or immediately via an IMAP client.
```
