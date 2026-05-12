"""CLI entry point: argparse + dispatch."""

import argparse
import sys
import traceback

from nsp import __version__
from nsp import allocator, parser as request_parser
from nsp.errors import NSPError
from nsp.formatters import available_formats, get_renderer


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nsp",
        description="Network Segment Partition — VLSM helper for IPv4.",
    )
    p.add_argument("-c", "--cidr", required=True,
                   help="Parent CIDR, e.g. 10.10.0.0/16")
    p.add_argument("-m", "--mask", required=True, nargs="+",
                   help="Subnet requests: /N or label=/N, e.g. web=/19 /20 /21")
    p.add_argument("-s", "--sort", action="store_true",
                   help="Internally sort requests largest-first to avoid alignment gaps")
    p.add_argument("-o", "--order", choices=["input", "address"], default="input",
                   help="Output row order (default: input)")
    p.add_argument("-f", "--format", choices=available_formats(), default="table",
                   help="Output format (default: table)")
    p.add_argument("-v", "--version", action="version", version=f"nsp {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        parent = request_parser.parse_parent_cidr(args.cidr)
        requests = request_parser.parse_requests(args.mask)
        result = allocator.allocate(
            parent, requests, sort=args.sort, order=args.order
        )
    except NSPError as e:
        print(f"error: {e}", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        print(f"unexpected error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 99

    renderer = get_renderer(args.format)
    if args.format in ("json", "yaml"):
        output = renderer(result, order=args.order)
    else:
        output = renderer(result)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
