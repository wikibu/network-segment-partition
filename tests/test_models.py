from ipaddress import IPv4Network

import pytest

from nsp.models import SubnetRequest, Allocation, PartitionResult


def test_subnet_request_construction():
    r = SubnetRequest(prefix_length=19, label="web", order=0)
    assert r.prefix_length == 19
    assert r.label == "web"
    assert r.order == 0


def test_subnet_request_defaults():
    r = SubnetRequest(prefix_length=20)
    assert r.label is None
    assert r.order == 0


def test_subnet_request_is_frozen():
    r = SubnetRequest(prefix_length=19)
    with pytest.raises(Exception):  # FrozenInstanceError
        r.prefix_length = 20  # type: ignore[misc]


def test_allocation_construction():
    req = SubnetRequest(prefix_length=19, label="web")
    net = IPv4Network("10.10.0.0/19")
    a = Allocation(request=req, network=net)
    assert a.request is req
    assert a.network == net


def test_partition_result_construction():
    parent = IPv4Network("10.10.0.0/16")
    req = SubnetRequest(prefix_length=19, label="web")
    alloc = Allocation(request=req, network=IPv4Network("10.10.0.0/19"))
    remaining = (IPv4Network("10.10.32.0/19"),)
    result = PartitionResult(
        parent=parent,
        allocations=(alloc,),
        remaining=remaining,
        sorted_internally=False,
    )
    assert result.parent == parent
    assert result.allocations == (alloc,)
    assert result.remaining == remaining
    assert result.sorted_internally is False


def test_partition_result_is_frozen():
    parent = IPv4Network("10.10.0.0/16")
    result = PartitionResult(parent=parent, allocations=(), remaining=(),
                             sorted_internally=False)
    with pytest.raises(Exception):
        result.parent = IPv4Network("10.0.0.0/8")  # type: ignore[misc]
