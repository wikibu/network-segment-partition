"""Plain CIDR-per-line formatter."""

from nsp.models import PartitionResult


def render(result: PartitionResult) -> str:
    lines = [str(a.network) for a in result.allocations]
    lines.extend(str(n) for n in result.remaining)
    return "\n".join(lines)
