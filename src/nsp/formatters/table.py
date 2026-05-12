"""Human-readable table formatter — stdlib only."""

from ipaddress import IPv4Network

from nsp.models import Allocation, PartitionResult


_COL_GAP = 4


def render(result: PartitionResult) -> str:
    lines: list[str] = []
    lines.append(f"Parent: {result.parent}   ({result.parent.num_addresses} addresses)")
    lines.append("")

    lines.append(f"Allocated ({len(result.allocations)}):")
    if result.allocations:
        rows = [_allocated_row(a, i + 1) for i, a in enumerate(result.allocations)]
        headers = ["#", "CIDR", "MASK", "SIZE", "RANGE", "LABEL"]
        align = ["right", "left", "left", "right", "left", "left"]
        lines.extend(_render_table(headers, rows, align, indent=2))
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"Remaining ({len(result.remaining)}):")
    if result.remaining:
        rows = [_remaining_row(n, i + 1) for i, n in enumerate(result.remaining)]
        headers = ["#", "CIDR", "MASK", "SIZE", "RANGE"]
        align = ["right", "left", "left", "right", "left"]
        lines.extend(_render_table(headers, rows, align, indent=2))
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def _allocated_row(a: Allocation, index: int) -> list[str]:
    net = a.network
    return [
        str(index),
        str(net),
        str(net.netmask),
        str(net.num_addresses),
        f"{net.network_address} - {net.broadcast_address}",
        a.request.label or "-",
    ]


def _remaining_row(net: IPv4Network, index: int) -> list[str]:
    return [
        str(index),
        str(net),
        str(net.netmask),
        str(net.num_addresses),
        f"{net.network_address} - {net.broadcast_address}",
    ]


def _render_table(headers: list[str], rows: list[list[str]],
                  align: list[str], indent: int) -> list[str]:
    cols = len(headers)
    widths = [
        max(len(headers[c]), max((len(r[c]) for r in rows), default=0))
        for c in range(cols)
    ]
    gap = " " * _COL_GAP
    prefix = " " * indent

    def fmt_cell(value: str, width: int, alignment: str, is_last: bool) -> str:
        if is_last:
            return value
        return value.rjust(width) if alignment == "right" else value.ljust(width)

    out: list[str] = []
    out.append(prefix + gap.join(
        fmt_cell(headers[c], widths[c], align[c], is_last=(c == cols - 1))
        for c in range(cols)
    ))
    for r in rows:
        out.append(prefix + gap.join(
            fmt_cell(r[c], widths[c], align[c], is_last=(c == cols - 1))
            for c in range(cols)
        ))
    return out
