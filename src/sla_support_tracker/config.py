"""Настройки подключения к PostgreSQL и n8n, читаются из переменных окружения и файла .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Параметры подключения Python-кода к PostgreSQL и к webhook n8n.

    По умолчанию используются порты 5433 (база) и 5679 (n8n), на которых контейнеры
    опубликованы на хосте.
    """

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = '127.0.0.1'
    postgres_port: int = 5433
    n8n_port: int = 5679


@lru_cache
def get_settings() -> Settings:
    """Необходимые настройки. Запускается 1 раз."""
    return Settings()
