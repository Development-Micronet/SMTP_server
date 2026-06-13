#!/bin/sh
set -e
sed -i "s|__SQL_RO_USER__|${SQL_RO_USER}|; s|__SQL_RO_PASSWORD__|${SQL_RO_PASSWORD}|; s|__POSTGRES_DB__|${POSTGRES_DB}|" \
    /etc/dovecot/dovecot-sql.conf.ext
# Master user password file (webmail service credential).
printf '%s:{ARGON2ID}%s\n' "${DOVECOT_MASTER_USER}" \
  "$(doveadm pw -s ARGON2ID -p "${DOVECOT_MASTER_PASSWORD}" | sed 's/{ARGON2ID}//')" \
  > /etc/dovecot/master-users
chown dovecot:dovecot /etc/dovecot/master-users
chmod 600 /etc/dovecot/master-users
exec dovecot -F
