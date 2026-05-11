from ipaddress import IPv4Network

import pytest

from nsp.allocator import allocate
from nsp.errors import CapacityExceededError
from nsp.models import SubnetRequest


def _reqs(*prefixes: int) -> list[SubnetRequest]:
    """Helper: build unlabeled requests from prefix lengths, preserving order."""
    return [SubnetRequest(prefix_length=p, order=i) for i, p in enumerate(prefixes)]


def test_original_user_example():
    """Reproduce the example from the spec: 8 requests in /16."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(19, 20, 21, 21, 19, 20, 21, 21)

    result = allocate(parent, reqs, sort=False, order="input")

    expected_cidrs = [
        "10.10.0.0/19", "10.10.32.0/20", "10.10.48.0/21", "10.10.56.0/21",
        "10.10.64.0/19", "10.10.96.0/20", "10.10.112.0/21", "10.10.120.0/21",
    ]
    actual = [str(a.network) for a in result.allocations]
    assert actual == expected_cidrs


def test_alignment_creates_gaps():
    """/21 then /19 in /16: /19 must skip to next /19 boundary, creating a gap."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(21, 19)

    result = allocate(parent, reqs, sort=False, order="input")

    assert [str(a.network) for a in result.allocations] == [
        "10.10.0.0/21",   # first /21
        "10.10.32.0/19",  # /19 aligned, gap 10.10.8.0 - 10.10.31.255
    ]


def test_alignment_overflow_at_top_of_ipv4_space():
    """Alignment that pushes cursor to 2**32 must raise CapacityExceededError,
    not AddressValueError."""
    parent = IPv4Network("0.0.0.0/0")
    reqs = _reqs(2, 1, 2)  # total = 2**30 + 2**31 + 2**30 = 2**32 = parent capacity exactly
    with pytest.raises(CapacityExceededError):
        allocate(parent, reqs, sort=False, order="input")


def test_remaining_collapsed_max_aggregation():
    """Spec example: after 8 subnets in /16, remaining 128.0/18 + 192.0/18 collapse to /17."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(19, 20, 21, 21, 19, 20, 21, 21)

    result = allocate(parent, reqs, sort=False, order="input")

    assert [str(n) for n in result.remaining] == ["10.10.128.0/17"]


def test_remaining_when_gaps_exist():
    """Sequential /21 then /19 in /16 leaves a gap at 10.10.8.0 - 10.10.31.255."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(21, 19)

    result = allocate(parent, reqs, sort=False, order="input")
    remaining_strs = [str(n) for n in result.remaining]

    # Gap 10.10.8.0 - 10.10.31.255 plus the rest after /19 (64.0 - 255.255)
    # Gap is 24 addresses worth — but in /N form: 8.0/21, 16.0/20
    # Rest: 64.0/18, 128.0/17
    assert "10.10.8.0/21" in remaining_strs
    assert "10.10.16.0/20" in remaining_strs
    assert "10.10.64.0/18" in remaining_strs
    assert "10.10.128.0/17" in remaining_strs
    # Ordered by start address
    starts = [int(n.network_address) for n in result.remaining]
    assert starts == sorted(starts)


def test_remaining_empty_when_fully_packed():
    """Two /17s exactly fill a /16."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(17, 17)

    result = allocate(parent, reqs, sort=False, order="input")
    assert result.remaining == ()
