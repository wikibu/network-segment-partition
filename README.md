# nsp — Network Segment Partition

A small CLI for VLSM (Variable Length Subnet Masking) on IPv4. Give it a parent
CIDR and a list of subnet sizes; it returns the allocated CIDRs plus any
unallocated space (collapsed to maximal blocks).

## Install

```bash
pip install -e .
```

Requires Python 3.10+.

## Usage

```bash
# Basic
nsp -c 10.10.0.0/16 -m /19 /20 /21 /21 /19 /20 /21 /21

# Labeled subnets
nsp -c 10.10.0.0/16 -m web=/19 db=/20 cache=/21 backup=/21

# Pack tightly (avoid alignment gaps when input order isn't optimal)
nsp -c 10.10.0.0/16 -m web=/21 db=/19 cache=/20 -s

# JSON output for scripting
nsp -c 10.10.0.0/16 -m web=/19 db=/20 -f json

# One CIDR per line for piping
nsp -c 10.10.0.0/16 -m /19 /20 -f plain | xargs -I {} echo "subnet: {}"
```

## Options

| Short | Long | Default | Description |
|---|---|---|---|
| `-c` | `--cidr` | required | Parent CIDR, e.g. `10.10.0.0/16` |
| `-m` | `--mask` | required | Subnet requests: `/N` or `label=/N` |
| `-s` | `--sort` | off | Internally sort largest-first to avoid alignment gaps |
| `-o` | `--order` | `input` | Output row order: `input` or `address` |
| `-f` | `--format` | `table` | Output format: `table`, `json`, `yaml`, `csv`, `plain` |
| `-v` | `--version` | — | Print version |
| `-h` | `--help` | — | Print help |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Business error (invalid CIDR, capacity exceeded, subnet too large, etc.) |
| 2 | argparse error (missing argument, invalid choice) |
| 99 | Unexpected exception |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest
```

## Design

See `docs/superpowers/specs/2026-05-12-nsp-design.md`.
