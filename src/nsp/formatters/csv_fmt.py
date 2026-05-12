"""CSV formatter — single file with a 'section' column distinguishing
allocated vs remaining rows."""

import csv
from io import StringIO

from nsp.models import PartitionResult


_HEADER = [
    "section", "index", "cidr", "mask", "prefix_length",
    "size", "range_start", "range_end", "label",
]


def render(result: PartitionResult) -> str:
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_HEADER)

    for i, a in enumerate(result.allocations, start=1):
        net = a.network
        writer.writerow([
            "allocated", i, str(net), str(net.netmask), net.prefixlen,
            net.num_addresses, str(net.network_address), str(net.broadcast_address),
            a.request.label or "",
        ])

    for i, net in enumerate(result.remaining, start=1):
        writer.writerow([
            "remaining", i, str(net), str(net.netmask), net.prefixlen,
            net.num_addresses, str(net.network_address), str(net.broadcast_address),
            "",
        ])

    return buf.getvalue().rstrip("\n")
