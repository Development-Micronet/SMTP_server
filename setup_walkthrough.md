# MailStack + AWS SES Self-Hosted Mail Server Setup Guide

This guide walks through setting up the **MailStack** platform on a fresh domain, incorporating all the configuration fixes, firewall settings, and optimizations we implemented for `polynexus.in`.

---

## 1. Domain & DNS Configuration (GoDaddy)

When setting up your domain DNS manager, you need to point traffic to your mail server and authorize outbound sending services.

### DNS Records to Create:
| Type | Name / Host | Value / Target | Priority | Description |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `mail` | `[Your Server Public IP]` | - | Maps `mail.domain.com` to your server. |
| **MX** | `@` | `mail.domain.com` | `10` | Routes incoming mail to your mail server. |
| **TXT** | `@` | `v=spf1 include:amazonses.com mx ~all` | - | Authorizes AWS SES and your MX server to send outbound mail. |
| **TXT** | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@domain.com` | - | Anti-spoofing policy (start in monitoring mode). |

> [!WARNING]
> **Check for Duplicate SPF Records:** Ensure you only have **one** TXT record starting with `v=spf1`. Multiple SPF records are invalid and will cause email providers like Gmail to mark all your emails as spam.

---

## 2. Firewall & AWS Network Configuration

Mail servers require several ports to be accessible from the internet. You must open these in both your **AWS Security Group** (Inbound Rules) and your **Ubuntu VM Firewall** (`ufw`).

### Ports to Open:
* **`25` (SMTP):** Required for other mail servers (like Google, Yahoo) to send inbound emails to you.
* **`587` (SMTP Submission):** Required for mail clients/webmail to send outgoing email.
* **`993` (IMAPS):** Required for clients to connect securely and read emails.
* **`80` / `443` (HTTP/HTTPS):** Required for the webmail UI and Let's Encrypt certificates.

### Commands to Run on the VM (UFW Firewall):
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 25/tcp
sudo ufw allow 587/tcp
sudo ufw allow 993/tcp
sudo ufw enable
```

---

## 3. Outbound Mail Relay Setup (AWS SES)

To achieve high deliverability, outbound emails are relayed through **AWS SES**.

1. **Verify Your Domain:**
   * Go to **AWS Console** -> **Amazon SES** -> **Verified Identities** -> **Create Identity** -> **Domain**.
   * Add your domain. AWS will generate **3 CNAME records** for Easy DKIM.
   * Add these 3 CNAMEs to GoDaddy. 
   > [!IMPORTANT]
   > When adding CNAME records to GoDaddy, do **not** copy the `.domain.com` suffix into the Host field. GoDaddy appends it automatically. For example, if AWS gives you `abc._domainkey.domain.com`, enter `abc._domainkey` in GoDaddy.
2. **Generate SMTP Credentials:**
   * In AWS SES, go to **SMTP Settings** -> **Create SMTP Credentials**.
   * Copy the generated **SMTP Username** and **SMTP Password**.
3. **Request Sandbox Exit:**
   * By default, your AWS SES account is in **Sandbox Mode**. You can only send mail to verified emails.
   * Go to the SES Dashboard, click **Request Production Access**, fill out the description, and submit.

---

## 4. MailStack Codebase & Configuration Adjustments

Before starting the Docker containers, apply the following config files to ensure stability and seamless updates.

### A. Environment Configuration (`.env`)
Create a `.env` file from `.env.example` and fill it out:
```ini
MAIL_DOMAIN=yourdomain.com
MAIL_HOSTNAME=mail.yourdomain.com

POSTGRES_DB=mailstack
POSTGRES_USER=mailstack
POSTGRES_PASSWORD=your_secure_password
SQL_RO_USER=mailro
SQL_RO_PASSWORD=your_readonly_password

DJANGO_SECRET_KEY=your_django_secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=mail.yourdomain.com

DOVECOT_MASTER_USER=webmail
DOVECOT_MASTER_PASSWORD=your_dovecot_master_password
SUBMISSION_USER=noreply@yourdomain.com
SUBMISSION_PASSWORD=your_submission_password

# AWS SES SMTP Credentials
RELAYHOST=email-smtp.ap-south-1.amazonaws.com # Adjust region if needed
RELAYHOST_USER=YOUR_AWS_SMTP_USERNAME
RELAYHOST_PASSWORD=YOUR_AWS_SMTP_PASSWORD
```

### B. Fix Postfix Config (`compose/postfix/main.cf`)
Ensure that inline comments are removed from `main.cf`, as Postfix reads them as part of the configuration value and crashes:
```postfix
# Correct syntax (no inline comments):
smtpd_tls_security_level = may
smtp_tls_security_level  = may
smtpd_tls_protocols = >=TLSv1.2
smtpd_tls_loglevel = 1
smtpd_sasl_auth_enable = no

# Anti-abuse (Spamhaus disabled to prevent public DNS resolver errors):
postscreen_greet_action = enforce
smtpd_helo_required = yes
smtpd_recipient_restrictions =
    permit_mynetworks,
    reject_unauth_destination,
    reject_unknown_reverse_client_hostname
smtpd_client_connection_rate_limit = 30
```

### C. Live Config Mounts (`compose/postfix/entrypoint.sh`)
Update the Postfix entrypoint script so that configuration changes made on the host apply instantly on container restart without needing to rebuild the Docker image:
```sh
#!/bin/sh
set -e

# Copy config files from host mount to live config directory on startup
if [ -d /etc/postfix/conf.d ]; then
  cp /etc/postfix/conf.d/main.cf /etc/postfix/main.cf
  cp /etc/postfix/conf.d/master.cf /etc/postfix/master.cf
  cp /etc/postfix/conf.d/pgsql-*.cf /etc/postfix/
fi

# Substitute env vars into lookup maps and main.cf at boot.
for f in /etc/postfix/pgsql-*.cf; do
  sed -i "s|__SQL_RO_USER__|${SQL_RO_USER}|; s|__SQL_RO_PASSWORD__|${SQL_RO_PASSWORD}|; s|__POSTGRES_DB__|${POSTGRES_DB}|" "$f"
done
postconf -e "myhostname = ${MAIL_HOSTNAME}"
if [ -n "${RELAYHOST}" ]; then
  postconf -e "relayhost = [${RELAYHOST}]:587" \
             "smtp_sasl_auth_enable = yes" \
             "smtp_sasl_password_maps = static:${RELAYHOST_USER}:${RELAYHOST_PASSWORD}" \
             "smtp_sasl_security_options = noanonymous" \
             "smtp_tls_security_level = encrypt"
fi

if [ -n "${SUBMISSION_USER}" ]; then
  echo "${SUBMISSION_USER} OK" > /etc/postfix/sasl_access
fi

exec postfix start-fg
```
Ensure you make the file executable on the VM host:
```bash
chmod +x compose/postfix/entrypoint.sh
```

### D. Optimize Indexing on Webpage Load (`webmail/views.py`)
To prevent the user from waiting 5 minutes for background tasks to index new emails, trigger Dovecot indexing synchronously when they open/refresh their inbox:
```python
@login_required
def inbox(request, folder: str = "INBOX"):
    mb = _mailbox_or_404(request)

    # Sync new mail from Dovecot on inbox load / refresh
    from mail.tasks import index_mailbox
    try:
        index_mailbox.run(None, mb.id, folder)
    except Exception:
        pass

    qs = MessageMeta.objects.filter(mailbox=mb, folder=folder)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "webmail/inbox.html",
                  {"mailbox": mb, "folder": folder, "page": page})
```

### E. Change Celery Schedule (`config/settings.py`)
Change the scheduled indexing fallback interval from 5 minutes (300 seconds) to 30 seconds:
```python
CELERY_BEAT_SCHEDULE = {
    "index-all-mailboxes": {
        "task": "mail.tasks.index_all_mailboxes",
        "schedule": 30.0,  # every 30 seconds
    },
}
```

---

## 5. Starting the Mail Platform

Once all configurations are written:

1. **Build and start the containers:**
   ```bash
   sudo docker compose up -d --build
   ```
2. **Run migrations to set up the Django database:**
   ```bash
   sudo docker compose exec django python manage.py migrate
   ```
3. **Create your admin user:**
   ```bash
   sudo docker compose exec django python manage.py createsuperuser
   ```
4. **Provision your mailboxes:**
   ```bash
   sudo docker compose exec django python manage.py adduser ADDR=testuser@domain.com PASS='your_mailbox_password'
   ```

At this stage, you can log in to your webmail interface and send/receive emails!
