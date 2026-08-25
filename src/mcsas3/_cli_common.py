from __future__ import annotations

from pathlib import Path


def validate_existing_file(_instance, attribute, value: Path) -> None:
    if not value.exists():
        raise FileNotFoundError(f"{attribute.name} file {value} must exist")


def validate_yaml_file(_instance, attribute, value: Path) -> None:
    validate_existing_file(_instance, attribute, value)
    if value.suffix != ".yaml":
        raise ValueError(f"{attribute.name} file must be a yaml file and end in .yaml")
