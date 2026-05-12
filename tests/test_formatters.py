import json

from nsp.formatters.json_fmt import render as render_json
from nsp.formatters.plain import render as render_plain


def test_plain_lists_allocated_then_remaining(sample_result):
    out = render_plain(sample_result)
    lines = out.splitlines()
    assert lines == [
        "10.10.0.0/19",
        "10.10.32.0/20",
        "10.10.48.0/21",
        "10.10.56.0/21",
        "10.10.64.0/18",
        "10.10.128.0/17",
    ]


def test_json_structure(sample_result):
    parsed = json.loads(render_json(sample_result))
    assert parsed["parent"] == {"cidr": "10.10.0.0/16", "size": 65536}

    web = parsed["allocated"][0]
    assert web == {
        "index": 1,
        "cidr": "10.10.0.0/19",
        "mask": "255.255.224.0",
        "prefix_length": 19,
        "size": 8192,
        "range": {"start": "10.10.0.0", "end": "10.10.31.255"},
        "label": "web",
    }
    assert list(web.keys()) == [
        "index", "cidr", "mask", "prefix_length", "size", "range", "label"
    ]

    rem0 = parsed["remaining"][0]
    assert rem0 == {
        "index": 1,
        "cidr": "10.10.64.0/18",
        "mask": "255.255.192.0",
        "prefix_length": 18,
        "size": 16384,
        "range": {"start": "10.10.64.0", "end": "10.10.127.255"},
    }
    assert "label" not in rem0

    assert parsed["meta"] == {
        "sorted_internally": False,
        "order": "input",
        "version": "0.1.0",
    }


def test_json_null_label_for_unnamed():
    from ipaddress import IPv4Network as N
    from nsp.models import Allocation, PartitionResult, SubnetRequest

    res = PartitionResult(
        parent=N("10.0.0.0/16"),
        allocations=(Allocation(SubnetRequest(20, None, 0), N("10.0.0.0/20")),),
        remaining=(),
        sorted_internally=False,
    )
    parsed = json.loads(render_json(res, order="input"))
    assert parsed["allocated"][0]["label"] is None
