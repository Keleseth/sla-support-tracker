.PHONY: install dev lint format typecheck test clean help docker-up docker-down db-apply

help:  ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## Установить зависимости для запуска и тестов
	python -m pip install -r requirements.txt

dev:  ## Установить также ruff и mypy
	python -m pip install -r requirements-dev.txt

lint:  ## Проверить стиль и ошибки (Ruff)
	python -m ruff check src tests

format:  ## Отформатировать код (Ruff)
	python -m ruff format src tests

typecheck:  ## Проверить типы (mypy)
	python -m mypy src

test:  ## Запустить тесты (pytest)
	python -m pytest

docker-up:  ## Поднять PostgreSQL и n8n
	docker compose up -d

docker-down:  ## Остановить контейнеры (данные в volumes сохраняются)
	docker compose down

db-apply:  ## Применить SQL-скрипты к запущенной базе (повторный запуск безопасен)
	docker compose exec -T postgres sh -c 'for f in /docker-entrypoint-initdb.d/0[1-9]*.sql; do psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -f "$$f"; done'

clean:  ## Удалить кэши
	python -m ruff clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
