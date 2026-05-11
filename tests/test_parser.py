import pytest

from nsp.parser import parse_requests, parse_parent_cidr
from nsp.errors import InvalidCIDRError, InvalidRequestError


# ---- parse_parent_cidr ----

def test_parent_cidr_valid():
    net = parse_parent_cidr("10.10.0.0/16")
    assert str(net) == "10.10.0.0/16"


def test_parent_cidr_invalid_string():
    with pytest.raises(InvalidCIDRError):
        parse_parent_cidr("not-a-cidr")


def test_parent_cidr_host_bits_set():
    # Host bits set: 10.10.0.1 has bit 0 set, /16 mask zeros it
    # ipaddress strict=True rejects this; we want strict.
    with pytest.raises(InvalidCIDRError):
        parse_parent_cidr("10.10.0.1/16")


# ---- parse_requests: valid ----

def test_request_simple_prefix():
    reqs = parse_requests(["/19"])
    assert len(reqs) == 1
    assert reqs[0].prefix_length == 19
    assert reqs[0].label is None
    assert reqs[0].order == 0


def test_request_labeled():
    reqs = parse_requests(["web=/19"])
    assert reqs[0].label == "web"
    assert reqs[0].prefix_length == 19


def test_request_label_with_dash_underscore_digits():
    reqs = parse_requests(["abc_123-xy=/24"])
    assert reqs[0].label == "abc_123-xy"
    assert reqs[0].prefix_length == 24


def test_request_order_preserved():
    reqs = parse_requests(["web=/19", "/20", "db=/21"])
    assert [r.order for r in reqs] == [0, 1, 2]
    assert [r.label for r in reqs] == ["web", None, "db"]
    assert [r.prefix_length for r in reqs] == [19, 20, 21]


def test_request_boundary_prefixes():
    reqs = parse_requests(["/0", "/32"])
    assert [r.prefix_length for r in reqs] == [0, 32]


def test_request_duplicate_labels_allowed():
    reqs = parse_requests(["web=/19", "web=/20"])
    assert all(r.label == "web" for r in reqs)


# ---- parse_requests: invalid ----

@pytest.mark.parametrize("bad", [
    "19",          # no slash
    "/33",         # prefix out of range
    "/-1",         # negative prefix
    "web!=/19",    # invalid label char
    "=/19",        # empty label before =
    "web=",        # empty after =
    "/19/20",      # extra slash
    "",            # empty string
    "/",           # bare slash
    "web=/",       # empty prefix after label
    "web=/abc",    # non-numeric prefix
])
def test_request_invalid_raises(bad):
    with pytest.raises(InvalidRequestError):
        parse_requests([bad])
