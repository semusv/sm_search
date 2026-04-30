.PHONY: up migrate test

# Поднимает все контейнеры проекта в фоне.
up:
	docker compose up --build -d

# Применяет миграции БД до последней версии.
migrate:
	alembic upgrade head

# Запускает автотесты.
test:
	pytest -q
