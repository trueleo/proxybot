"""Support executing the CLI by doing `python -m proxybot`."""
from __future__ import annotations

from proxybot.cli import cli

if __name__ == "__main__":
    raise SystemExit(cli())
