"""VLSM allocation algorithm: sequential placement with optional sort."""

import ipaddress
from ipaddress import IPv4Network
from typing import Literal

from nsp.errors import CapacityExceededError, SubnetTooLargeError
from nsp.models import Allocation, PartitionResult, SubnetRequest


def allocate(
    parent: IPv4Network,
    requests: list[SubnetRequest],
    sort: bool,
    order: Literal["input", "address"],
) -> PartitionResult:
    """Allocate subnets in parent according to requests."""

    work_list = sorted(requests, key=lambda r: r.prefix_length) if sort else list(requests)

    cursor = int(parent.network_address)
    parent_end = int(parent.broadcast_address)
    allocations: list[Allocation] = []

    for req in work_list:
        block_size = 2 ** (32 - req.prefix_length)
        aligned = (cursor + block_size - 1) // block_size * block_size

        if aligned + block_size - 1 > parent_end:
            short_by = aligned + block_size - parent_end - 1
            if aligned >= (1 << 32):
                # Alignment overflowed beyond the top of IPv4 space; can't
                # render align_at as an IPv4 address. Fall back to the no-align form.
                raise CapacityExceededError(
                    short_by=short_by,
                    hint="alignment gaps consumed available space; try --sort",
                )
            raise CapacityExceededError(
                short_by=short_by,
                hint="alignment gaps consumed available space; try --sort",
                align_at=str(ipaddress.IPv4Address(aligned)),
                align_prefix=req.prefix_length,
            )

        network = IPv4Network((aligned, req.prefix_length))
        allocations.append(Allocation(request=req, network=network))
        cursor = aligned + block_size

    if order == "input":
        allocations.sort(key=lambda a: a.request.order)
    else:
        allocations.sort(key=lambda a: int(a.network.network_address))

    return PartitionResult(
        parent=parent,
        allocations=tuple(allocations),
        remaining=(),  # filled in by Task 6
        sorted_internally=sort,
    )
