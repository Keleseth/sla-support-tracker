.PHONY: install dev lint format typecheck test clean help docker-up docker-down db-apply send-fixtures report

AS_OF ?= 2026-09-08T12:00:00+03:00

help:  ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  %-14s %s\n", $$1, $$2}'

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

send-fixtures:  ## Отправить сценарии из fixtures на webhook n8n и сверить ответы (нужны пустая база и опубликованный workflow с созданным кредом)
	python -m sla_support_tracker.send_fixtures

report:  ## Построить report.csv, data_issues.csv и summary.json в output/ на момент AS_OF (make report AS_OF=2026-09-08T12:00:00+03:00)
	python -m sla_support_tracker.cli --as-of "$(AS_OF)"

clean:  ## Удалить кэши
	python -m ruff clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
