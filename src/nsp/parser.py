"""Parse CLI string arguments into typed model objects."""

import re
from ipaddress import IPv4Network, AddressValueError, NetmaskValueError

from nsp.errors import InvalidCIDRError, InvalidRequestError
from nsp.models import SubnetRequest


_LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_PREFIX_RE = re.compile(r"^/(\d+)$")
_LABELED_RE = re.compile(r"^([^=]+)=(/.+)$")


def parse_parent_cidr(value: str) -> IPv4Network:
    """Strict IPv4 CIDR parse. Rejects host-bit-set forms."""
    try:
        return IPv4Network(value, strict=True)
    except (ValueError, AddressValueError, NetmaskValueError) as e:
        raise InvalidCIDRError(value) from e


def parse_requests(raw_items: list[str]) -> list[SubnetRequest]:
    """Parse one or more -m entries into SubnetRequest list, preserving order."""
    return [_parse_one(raw, idx) for idx, raw in enumerate(raw_items)]


def _parse_one(raw: str, order: int) -> SubnetRequest:
    if not raw:
        raise InvalidRequestError(raw, "entry is empty")

    label: str | None = None
    prefix_part = raw

    if "=" in raw:
        m = _LABELED_RE.match(raw)
        if not m:
            raise InvalidRequestError(raw, "expected format: label=/N or /N")
        label_part, prefix_part = m.group(1), m.group(2)
        if not _LABEL_RE.match(label_part):
            raise InvalidRequestError(raw, "labels must match [A-Za-z0-9_-]+")
        label = label_part

    pm = _PREFIX_RE.match(prefix_part)
    if not pm:
        raise InvalidRequestError(raw, "expected format: /N (N is an integer)")
    prefix_length = int(pm.group(1))
    if not (0 <= prefix_length <= 32):
        raise InvalidRequestError(raw, f"prefix must be in [0, 32], got /{prefix_length}")

    return SubnetRequest(prefix_length=prefix_length, label=label, order=order)
