"""Отправка файлов с событиями на webhook n8n."""

import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sla_support_tracker.config import get_settings

FIXTURES_DIR = Path('fixtures')
COUNTER_KEYS = ('received', 'inserted', 'duplicates', 'rejected')


def send_file(path: Path, url: str) -> tuple[int, dict[str, Any]]:
    """
    Отправляет содержимое файла POST-запросом на webhook. Получает код ответа и тело.

    Тело ответа разбирается как JSON и при кодах ошибок 4xx и 5xx.
    """
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def check_response(status: int, body: dict[str, Any], expected: dict[str, int] | None) -> list[str]:
    """Расхождения ответа с ожидаемым: код 200 и счётчики, если они заданы в манифесте."""
    problems = []
    if status != 200:
        problems.append(f'код ответа {status}, ожидался 200')
    if expected is not None:
        for key in COUNTER_KEYS:
            if body.get(key) != expected[key]:
                problems.append(f'{key}: получено {body.get(key)}, ожидалось {expected[key]}')
    return problems


def main() -> int:
    """
    Отправляет файлы всех сценариев на webhook в порядке манифеста и сверяет ответы.

    Ожидаемые счётчики в манифесте относятся к пустой базе. Возвращает 0, если расхождений нет.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding='utf-8')
    manifest = json.loads((FIXTURES_DIR / 'expected_results.json').read_text(encoding='utf-8'))
    url = f'http://127.0.0.1:{get_settings().n8n_port}/webhook/events'
    problems_found = 0
    try:
        for scenario in manifest['scenarios']:
            attempts = 2 if scenario.get('send_twice') else 1
            for name in scenario['files']:
                for attempt in range(attempts):
                    status, body = send_file(FIXTURES_DIR / 'scenarios' / name, url)
                    key = 'expected_second_response' if attempt == 1 else 'expected_first_response'
                    problems = check_response(status, body, scenario.get(key))
                    counters = {key: body.get(key) for key in COUNTER_KEYS}
                    print(f'#{scenario["number"]:>2} {name} (отправка {attempt + 1}): {counters}')
                    for problem in problems:
                        print(f'    РАСХОЖДЕНИЕ: {problem}')
                    problems_found += len(problems)
    except urllib.error.URLError as error:
        print(f'Webhook недоступен ({error.reason}): запустите контейнеры и опубликуйте workflow.')
        return 1
    print('Расхождений нет.' if problems_found == 0 else f'Расхождений: {problems_found}.')
    return 0 if problems_found == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
