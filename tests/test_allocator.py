from ipaddress import IPv4Network

import pytest

from nsp.allocator import allocate
from nsp.errors import CapacityExceededError, SubnetTooLargeError
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
    # Exact length asserted to catch spurious extra blocks (spec invariant: smallest possible set).
    assert len(result.remaining) == 4
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


def test_capacity_exceeded_pre_check():
    """Three /25 (384 addresses) cannot fit in a /24 (256)."""
    parent = IPv4Network("10.10.0.0/24")
    reqs = _reqs(25, 25, 25)

    with pytest.raises(CapacityExceededError) as exc:
        allocate(parent, reqs, sort=False, order="input")

    assert exc.value.requested == 384  # 3 * 128
    assert exc.value.available == 256
    assert exc.value.short_by == 128


def test_subnet_too_large():
    """A /15 cannot fit in a /16 parent."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(15)

    with pytest.raises(SubnetTooLargeError) as exc:
        allocate(parent, reqs, sort=False, order="input")
    assert exc.value.request_prefix == 15


def test_subnet_equal_to_parent_succeeds():
    """A /16 mask in a /16 parent fills it exactly."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(16)

    result = allocate(parent, reqs, sort=False, order="input")
    assert [str(a.network) for a in result.allocations] == ["10.10.0.0/16"]
    assert result.remaining == ()


def test_alignment_capacity_error_suggests_sort():
    """Order producing alignment gaps that overflow should hint --sort.

    parent /23 (512), reqs [/25 (128), /24 (256), /25 (128)] total 512 = parent
      /25 at 0 → cursor 128
      /24 aligns to 256 → end 511, cursor 512
      /25 aligns to 512 — beyond parent end (511). Overflow!
    """
    parent = IPv4Network("10.10.0.0/23")
    reqs = _reqs(25, 24, 25)  # 128 + 256 + 128 = 512 exact

    with pytest.raises(CapacityExceededError) as exc:
        allocate(parent, reqs, sort=False, order="input")

    assert exc.value.hint is not None
    assert "--sort" in exc.value.hint
    assert exc.value.align_prefix == 25


def test_sort_packs_tightly():
    """Same input that produces gaps without --sort packs without gaps with --sort."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(21, 19)

    result = allocate(parent, reqs, sort=True, order="input")

    networks = {str(a.network) for a in result.allocations}
    assert networks == {"10.10.0.0/19", "10.10.32.0/21"}
    # Remaining is the rest: 40.0/21 + 48.0/20 + 64.0/18 + 128.0/17 collapse to 40.0/21, 48.0/20, 64.0/18, 128.0/17
    # Just verify no gaps in the allocated range (no /21-sized block missing under 10.10.32.0)
    for r in result.remaining:
        assert int(r.network_address) >= int(IPv4Network("10.10.40.0/21").network_address)


def test_order_input_preserves_input_order():
    parent = IPv4Network("10.10.0.0/16")
    reqs = [
        SubnetRequest(prefix_length=21, label="web", order=0),
        SubnetRequest(prefix_length=19, label="db", order=1),
        SubnetRequest(prefix_length=20, label="cache", order=2),
    ]
    result = allocate(parent, reqs, sort=True, order="input")
    labels = [a.request.label for a in result.allocations]
    assert labels == ["web", "db", "cache"]


def test_order_address_sorts_by_address():
    parent = IPv4Network("10.10.0.0/16")
    reqs = [
        SubnetRequest(prefix_length=21, label="web", order=0),
        SubnetRequest(prefix_length=19, label="db", order=1),
        SubnetRequest(prefix_length=20, label="cache", order=2),
    ]
    result = allocate(parent, reqs, sort=True, order="address")
    addrs = [int(a.network.network_address) for a in result.allocations]
    assert addrs == sorted(addrs)
    # With --sort, db (/19) is placed first at 0, cache (/20) at 32.0, web (/21) at 48.0
    labels_in_addr_order = [a.request.label for a in result.allocations]
    assert labels_in_addr_order == ["db", "cache", "web"]


def test_sort_is_stable_for_equal_prefixes():
    """Two /21s with sort=True must keep their original relative order."""
    parent = IPv4Network("10.10.0.0/16")
    reqs = [
        SubnetRequest(prefix_length=21, label="first", order=0),
        SubnetRequest(prefix_length=21, label="second", order=1),
    ]
    result = allocate(parent, reqs, sort=True, order="address")
    # In address order: first must come before second
    addr_order = [a.request.label for a in result.allocations]
    assert addr_order == ["first", "second"]


def test_sorted_internally_flag():
    parent = IPv4Network("10.10.0.0/16")
    reqs = _reqs(19)

    assert allocate(parent, reqs, sort=False, order="input").sorted_internally is False
    assert allocate(parent, reqs, sort=True, order="input").sorted_internally is True


def test_slash_31_allowed():
    parent = IPv4Network("10.10.0.0/24")
    reqs = _reqs(31, 31)
    result = allocate(parent, reqs, sort=False, order="input")
    assert [str(a.network) for a in result.allocations] == [
        "10.10.0.0/31", "10.10.0.2/31"
    ]


def test_slash_32_allowed():
    parent = IPv4Network("10.10.0.0/24")
    reqs = _reqs(32, 32, 32)
    result = allocate(parent, reqs, sort=False, order="input")
    assert [str(a.network) for a in result.allocations] == [
        "10.10.0.0/32", "10.10.0.1/32", "10.10.0.2/32"
    ]


def test_parent_zero_zero():
    """parent 0.0.0.0/0 (entire IPv4 space) accepts /1 split."""
    parent = IPv4Network("0.0.0.0/0")
    reqs = _reqs(1, 1)
    result = allocate(parent, reqs, sort=False, order="input")
    assert [str(a.network) for a in result.allocations] == [
        "0.0.0.0/1", "128.0.0.0/1"
    ]
    assert result.remaining == ()
