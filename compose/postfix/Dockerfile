FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      postfix postfix-pgsql ca-certificates libsasl2-modules && rm -rf /var/lib/apt/lists/*
COPY main.cf master.cf /etc/postfix/
COPY pgsql-domains.cf pgsql-mailbox.cf pgsql-alias.cf /etc/postfix/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 25 587
ENTRYPOINT ["/entrypoint.sh"]
