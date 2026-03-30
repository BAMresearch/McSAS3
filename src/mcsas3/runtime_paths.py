"""Runtime path helpers for source and frozen standalone executions."""

from __future__ import annotations

import sys
from pathlib import Path


def _source_checkout_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runtime_resource_root() -> Path:
    """Return the directory that should contain bundled example and test resources."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _source_checkout_root()


def example_configuration_path(filename: str) -> Path:
    """Return a path inside the example configuration directory."""

    return runtime_resource_root() / "example_configurations" / filename


def quickstart_testdata_path(filename: str) -> Path:
    """Return a path inside the bundled or checkout test-data directory."""

    return runtime_resource_root() / "testdata" / filename
