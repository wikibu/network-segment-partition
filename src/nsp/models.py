"""Immutable data classes shared across the pipeline."""

from dataclasses import dataclass, field
from ipaddress import IPv4Network


@dataclass(frozen=True)
class SubnetRequest:
    """One parsed -m entry."""
    prefix_length: int
    label: str | None = None
    order: int = 0


@dataclass(frozen=True)
class Allocation:
    """One successfully allocated subnet, linked back to its request."""
    request: SubnetRequest
    network: IPv4Network


@dataclass(frozen=True)
class PartitionResult:
    """Final output of the allocator, consumed by formatters."""
    parent: IPv4Network
    allocations: tuple[Allocation, ...]
    remaining: tuple[IPv4Network, ...]
    sorted_internally: bool
