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

    # Pre-check 1: any single request bigger than parent
    for r in requests:
        if r.prefix_length < parent.prefixlen:
            raise SubnetTooLargeError(
                request_prefix=r.prefix_length,
                parent_cidr=str(parent),
            )

    # Pre-check 2: aggregate capacity
    requested_total = sum(2 ** (32 - r.prefix_length) for r in requests)
    parent_total = parent.num_addresses
    if requested_total > parent_total:
        raise CapacityExceededError(
            short_by=requested_total - parent_total,
            requested=requested_total,
            available=parent_total,
        )

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

    remaining_nets = _compute_remaining(parent, allocations)
    return PartitionResult(
        parent=parent,
        allocations=tuple(allocations),
        remaining=tuple(remaining_nets),
        sorted_internally=sort,
    )


def _compute_remaining(parent: IPv4Network,
                       allocations: list[Allocation]) -> list[IPv4Network]:
    """Subtract allocated subnets from parent, collapse to maximal CIDR blocks."""
    used = sorted({a.network for a in allocations},
                  key=lambda n: int(n.network_address))

    remaining: list[IPv4Network] = [parent]
    for used_net in used:
        new_remaining: list[IPv4Network] = []
        for r in remaining:
            if used_net.subnet_of(r):
                new_remaining.extend(r.address_exclude(used_net))
            else:
                new_remaining.append(r)
        remaining = new_remaining

    return list(ipaddress.collapse_addresses(remaining))
