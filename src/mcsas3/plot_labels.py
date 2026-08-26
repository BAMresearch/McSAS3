from __future__ import annotations

from .parameter_units import SIZE_PARAMETER_UNIT_LABEL, is_size_fit_parameter


def fit_parameter_axis_label(parameter: object) -> str:
    """Return the plot label for a fitted model parameter."""
    parameter_name = str(parameter)
    if is_size_fit_parameter(parameter_name):
        return f"{parameter_name} ({SIZE_PARAMETER_UNIT_LABEL})"
    return parameter_name
