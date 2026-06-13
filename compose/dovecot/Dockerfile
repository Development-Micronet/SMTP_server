FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      dovecot-imapd dovecot-lmtpd dovecot-pgsql dovecot-sieve dovecot-managesieved \
      ca-certificates && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 5000 vmail && useradd -u 5000 -g vmail -d /var/vmail -m vmail
COPY dovecot.conf /etc/dovecot/dovecot.conf
COPY dovecot-sql.conf.ext /etc/dovecot/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod 600 /etc/dovecot/dovecot-sql.conf.ext
EXPOSE 143 993 24 12345
ENTRYPOINT ["/entrypoint.sh"]
