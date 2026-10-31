"""Тесты разбора аргументов командной строки."""

import argparse
from datetime import timedelta
from pathlib import Path

import pytest

from sla_support_tracker.cli import build_parser, parse_as_of


def test_parse_as_of_accepts_offset() -> None:
    moment = parse_as_of('2026-09-08T12:00:00+03:00')
    assert moment.utcoffset() == timedelta(hours=3)


def test_parse_as_of_accepts_z_suffix() -> None:
    moment = parse_as_of('2026-09-08T09:00:00Z')
    assert moment.utcoffset() == timedelta(0)


@pytest.mark.parametrize('value', ['2026-09-08T12:00:00', '2026-09-08'])
def test_parse_as_of_rejects_missing_timezone(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_as_of(value)


@pytest.mark.parametrize('value', ['вчера', '', '2026-13-45T00:00:00+03:00'])
def test_parse_as_of_rejects_garbage(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_as_of(value)


def test_as_of_is_required() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args([])
    assert exit_info.value.code == 2


def test_output_dir_defaults_to_output() -> None:
    arguments = build_parser().parse_args(['--as-of', '2026-09-08T12:00:00+03:00'])
    assert arguments.output_dir == Path('output')
