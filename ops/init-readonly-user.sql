-- Read-only role used by Postfix and Dovecot lookup maps.
-- Password placeholder is replaced on first boot OR set it manually:
--   ALTER ROLE mailro PASSWORD '...';
CREATE ROLE mailro LOGIN PASSWORD 'CHANGEME-must-match-SQL_RO_PASSWORD';
GRANT CONNECT ON DATABASE mailstack TO mailro;
GRANT USAGE ON SCHEMA public TO mailro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mailro;
