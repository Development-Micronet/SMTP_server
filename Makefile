.PHONY: up down migrate superuser adduser test logs backup

up:            ## start the full stack
	docker compose up -d --build
down:
	docker compose down
migrate:
	docker compose exec django python manage.py migrate
superuser:
	docker compose exec django python manage.py createsuperuser
adduser:       ## make adduser ADDR=alice@example.com PASS=secret
	docker compose exec django python manage.py create_mailbox $(ADDR) $(PASS)
test:
	docker compose exec django pytest
logs:
	docker compose logs -f --tail=100 postfix dovecot django
backup:
	./ops/backup.sh
