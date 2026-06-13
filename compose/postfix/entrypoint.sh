#!/bin/sh
set -e

# Copy config files from host mount to live config directory
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

# Write the SASL access file for the Django submission user:
if [ -n "${SUBMISSION_USER}" ]; then
  echo "${SUBMISSION_USER} OK" > /etc/postfix/sasl_access
fi

exec postfix start-fg
