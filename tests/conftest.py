"""Shared pytest fixtures."""
from ipaddress import IPv4Network

import pytest

from nsp.models import Allocation, PartitionResult, SubnetRequest


@pytest.fixture
def sample_result() -> PartitionResult:
    """The spec's worked example: 10.10.0.0/16 + web=/19, db=/20, cache=/21, backup=/21."""
    parent = IPv4Network("10.10.0.0/16")
    allocations = (
        Allocation(SubnetRequest(19, "web", 0), IPv4Network("10.10.0.0/19")),
        Allocation(SubnetRequest(20, "db", 1), IPv4Network("10.10.32.0/20")),
        Allocation(SubnetRequest(21, "cache", 2), IPv4Network("10.10.48.0/21")),
        Allocation(SubnetRequest(21, "backup", 3), IPv4Network("10.10.56.0/21")),
    )
    remaining = (
        IPv4Network("10.10.64.0/18"),
        IPv4Network("10.10.128.0/17"),
    )
    return PartitionResult(parent, allocations, remaining, sorted_internally=False)
