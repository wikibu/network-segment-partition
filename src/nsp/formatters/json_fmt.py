"""JSON formatter."""

import json
from ipaddress import IPv4Network
from typing import Literal

from nsp import __version__
from nsp.models import Allocation, PartitionResult


def render(result: PartitionResult, order: Literal["input", "address"] = "input") -> str:
    payload = {
        "parent": {
            "cidr": str(result.parent),
            "size": result.parent.num_addresses,
        },
        "allocated": [_allocation_row(a, i + 1) for i, a in enumerate(result.allocations)],
        "remaining": [_remaining_row(n, i + 1) for i, n in enumerate(result.remaining)],
        "meta": {
            "sorted_internally": result.sorted_internally,
            "order": order,
            "version": __version__,
        },
    }
    return json.dumps(payload, indent=2)


def _allocation_row(a: Allocation, index: int) -> dict:
    net = a.network
    return {
        "index": index,
        "cidr": str(net),
        "mask": str(net.netmask),
        "prefix_length": net.prefixlen,
        "size": net.num_addresses,
        "range": {"start": str(net.network_address), "end": str(net.broadcast_address)},
        "label": a.request.label,
    }


def _remaining_row(net: IPv4Network, index: int) -> dict:
    return {
        "index": index,
        "cidr": str(net),
        "mask": str(net.netmask),
        "prefix_length": net.prefixlen,
        "size": net.num_addresses,
        "range": {"start": str(net.network_address), "end": str(net.broadcast_address)},
    }
