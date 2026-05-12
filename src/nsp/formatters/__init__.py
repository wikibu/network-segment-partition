"""Formatter dispatcher — maps --format string to renderer callable."""

from collections.abc import Callable

from nsp.formatters import csv_fmt, json_fmt, plain, table, yaml_fmt


_RENDERERS: dict[str, Callable[..., str]] = {
    "table": table.render,
    "json": json_fmt.render,
    "yaml": yaml_fmt.render,
    "csv": csv_fmt.render,
    "plain": plain.render,
}


def get_renderer(name: str) -> Callable[..., str]:
    if name not in _RENDERERS:
        raise ValueError(f"unknown format: {name}")
    return _RENDERERS[name]


def available_formats() -> list[str]:
    return list(_RENDERERS.keys())
