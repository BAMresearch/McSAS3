from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from .data_model import ureg

MCSAS_LENGTH_UNIT = ureg.Unit("nanometer")
SASMODELS_LENGTH_UNIT = ureg.Unit("angstrom")
MCSAS_Q_UNIT = ureg.Unit("1 / nanometer")
SASMODELS_Q_UNIT = ureg.Unit("1 / angstrom")
MCSAS_INTENSITY_UNIT = ureg.Unit("1 / meter / steradian")
SASMODELS_INTENSITY_UNIT = ureg.Unit("1 / centimeter / steradian")
SASMODELS_INTENSITY_TO_MCSAS = ureg.Quantity(1, SASMODELS_INTENSITY_UNIT).to(MCSAS_INTENSITY_UNIT).magnitude
SASMODELS_SCALE_TO_VOLUME_FRACTION = 1.0 / SASMODELS_INTENSITY_TO_MCSAS
LEGACY_CUSTOM_MODEL_SCALE_TO_VOLUME_FRACTION = 1e-5
SIZE_PARAMETER_UNIT_LABEL = "nm"

_SIZE_PARAMETER_TOKENS = frozenset(
    {
        "diameter",
        "distance",
        "height",
        "length",
        "radius",
        "rg",
        "spacing",
        "thickness",
        "width",
    }
)
_SIZE_PARAMETER_PREFIXES = ("thick",)
_NON_LENGTH_PARAMETER_SUFFIXES = ("_mode", "_pd", "_pd_n", "_pd_nsigma", "_pd_type")


def is_size_fit_parameter(parameter: str) -> bool:
    """Return whether a fitted model parameter is interpreted in canonical length units."""
    normalized = parameter.lower().replace("-", "_")
    if normalized.endswith(_NON_LENGTH_PARAMETER_SUFFIXES):
        return False

    tokens = [token for token in normalized.split("_") if token]
    return any(token in _SIZE_PARAMETER_TOKENS for token in tokens) or any(
        token.startswith(_SIZE_PARAMETER_PREFIXES) for token in tokens
    )


def is_sasmodels_length_unit(unit: object) -> bool:
    """Return whether a SasModels unit string describes a length value."""
    unit_text = str(unit).strip()
    if not unit_text:
        return False
    try:
        resolved_unit = ureg.Unit(unit_text.replace("Ang", "angstrom"))
    except Exception:
        return False
    return resolved_unit.dimensionality == MCSAS_LENGTH_UNIT.dimensionality


def sasmodels_length_parameter_ids(model_info: object) -> frozenset[str]:
    """Return SasModels parameter IDs declared with length units."""
    parameter_table = getattr(model_info, "parameters", None)
    parameters = getattr(parameter_table, "kernel_parameters", ())
    return frozenset(
        str(parameter.id) for parameter in parameters if is_sasmodels_length_unit(getattr(parameter, "units", ""))
    )


def mcsas_length_to_sasmodels(value: Any) -> Any:
    """Convert a McSAS3 canonical length value to SasModels' Angstrom convention."""
    return ureg.Quantity(value, MCSAS_LENGTH_UNIT).to(SASMODELS_LENGTH_UNIT).magnitude


def mcsas_q_to_sasmodels(value: Any) -> Any:
    """Convert a McSAS3 canonical Q value to SasModels' reciprocal Angstrom convention."""
    return ureg.Quantity(value, MCSAS_Q_UNIT).to(SASMODELS_Q_UNIT).magnitude


def sasmodels_parameter_values(
    parameters: Mapping[str, Any],
    *,
    length_parameters: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return model parameters converted from McSAS3 canonical units to SasModels units."""
    length_parameter_names = None if length_parameters is None else frozenset(length_parameters)
    converted = dict(parameters)
    for parameter, value in converted.items():
        is_length = (
            parameter in length_parameter_names
            if length_parameter_names is not None
            else is_size_fit_parameter(parameter)
        )
        if is_length:
            converted[parameter] = mcsas_length_to_sasmodels(value)
    return converted


def sasmodels_q_arrays(q_arrays: Iterable[np.ndarray]) -> list[np.ndarray]:
    """Return Q arrays converted from McSAS3 canonical units to SasModels units."""
    return [np.asarray(mcsas_q_to_sasmodels(q_component), dtype=float) for q_component in q_arrays]
