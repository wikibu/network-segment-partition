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
