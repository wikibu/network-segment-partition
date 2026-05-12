"""YAML formatter — reuses the same payload as JSON formatter."""

import json
from typing import Literal

import yaml

from nsp.formatters.json_fmt import render as _render_json
from nsp.models import PartitionResult


def render(result: PartitionResult, order: Literal["input", "address"] = "input") -> str:
    payload = json.loads(_render_json(result, order=order))
    return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
