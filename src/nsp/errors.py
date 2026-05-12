"""Business exceptions raised across nsp modules."""


class NSPError(Exception):
    """Base for all business errors. CLI maps exit_code to process exit."""
    exit_code: int = 1

    def message(self) -> str:
        return str(self)


class InvalidCIDRError(NSPError):
    """Parent CIDR string is malformed."""

    def __init__(self, value: str):
        self.value = value
        super().__init__(
            f"invalid CIDR '{value}'\n  → expected format: a.b.c.d/N"
        )


class InvalidRequestError(NSPError):
    """A single -m item is malformed."""

    def __init__(self, raw: str, reason: str):
        self.raw = raw
        self.reason = reason
        super().__init__(
            f"invalid '-m' entry '{raw}'\n  → {reason}"
        )


class SubnetTooLargeError(NSPError):
    """A single request's subnet is larger than the parent network."""

    def __init__(self, request_prefix: int, parent_cidr: str):
        self.request_prefix = request_prefix
        self.parent_cidr = parent_cidr
        parent_prefix = int(parent_cidr.split("/")[1])
        super().__init__(
            f"subnet /{request_prefix} is larger than parent {parent_cidr}\n"
            f"  → each subnet prefix must be >= {parent_prefix}"
        )


class CapacityExceededError(NSPError):
    """Requested space exceeds parent (pre-check or post-alignment)."""

    def __init__(
        self,
        short_by: int,
        requested: int | None = None,
        available: int | None = None,
        hint: str | None = None,
        align_at: str | None = None,
        align_prefix: int | None = None,
    ):
        self.short_by = short_by
        self.requested = requested
        self.available = available
        self.hint = hint
        self.align_at = align_at
        self.align_prefix = align_prefix

        lines: list[str] = []
        if align_at is not None and align_prefix is not None:
            lines.append(
                f"capacity exceeded after alignment: cannot fit /{align_prefix} at {align_at}"
            )
            lines.append(f"  → alignment gaps consumed {short_by} addresses")
        else:
            lines.append(
                f"capacity exceeded: requested {requested} addresses but parent has {available}"
            )
            lines.append(f"  → short by {short_by} addresses")
        if hint:
            lines.append(f"  → {hint}")
        super().__init__("\n".join(lines))
