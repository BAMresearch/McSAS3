from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .data_adapters import AnalysisDataDict, analysis_data_from_bundle


@dataclass(frozen=True)
class OptimizerInput:
    """Normalized optimizer-facing arrays for 1D or 2D scattering data."""

    q: tuple[np.ndarray, ...]
    i: np.ndarray
    isigma: np.ndarray

    def __post_init__(self) -> None:
        q_arrays = tuple(np.asarray(q_component, dtype=float).reshape(-1) for q_component in self.q)
        i_array = np.asarray(self.i, dtype=float).reshape(-1)
        isigma_array = np.asarray(self.isigma, dtype=float).reshape(-1)

        if len(q_arrays) not in (1, 2):
            raise ValueError("OptimizerInput expects one Q array for 1D data or two Q arrays for 2D data.")
        if i_array.size == 0:
            raise ValueError("OptimizerInput intensity array must not be empty.")
        if isigma_array.shape != i_array.shape:
            raise ValueError("OptimizerInput intensity and uncertainty arrays must have matching shapes.")
        if any(q_component.shape != i_array.shape for q_component in q_arrays):
            raise ValueError("All OptimizerInput Q arrays must match the intensity array shape.")

        object.__setattr__(self, "q", q_arrays)
        object.__setattr__(self, "i", i_array)
        object.__setattr__(self, "isigma", isigma_array)

    @property
    def ndim(self) -> int:
        """Return the dimensionality of the optimizer input."""

        return len(self.q)

    @property
    def q_for_model(self) -> list[np.ndarray]:
        """Return copied Q arrays ready for kernel construction."""

        return [q_component.copy() for q_component in self.q]

    @property
    def primary_q(self) -> np.ndarray:
        """Return the primary Q axis used for 1D support calculations."""

        return self.q[0]

    @property
    def q_support(self) -> np.ndarray:
        """Return absolute Q support for limit auto-scaling."""

        if self.ndim == 1:
            return np.abs(self.primary_q)
        return np.sqrt(np.sum(np.stack([q_component**2 for q_component in self.q], axis=0), axis=0))

    def to_analysis_data(self) -> AnalysisDataDict:
        """Project the normalized arrays into the flat legacy analysis-data dict."""

        return {
            "Q": [q_component.copy() for q_component in self.q],
            "I": self.i.copy(),
            "ISigma": self.isigma.copy(),
        }


def optimizer_input_from_analysis_data(analysis_data: Mapping[str, Any]) -> OptimizerInput:
    """Build normalized optimizer arrays from a flat analysis-data mapping."""

    required_keys = {"Q", "I", "ISigma"}
    missing_keys = required_keys.difference(analysis_data.keys())
    if missing_keys:
        raise KeyError(f"Analysis data is missing required keys: {sorted(missing_keys)}")

    q_value = analysis_data["Q"]
    if isinstance(q_value, np.ndarray):
        q_arrays = (np.asarray(q_value, dtype=float).reshape(-1),)
    else:
        if not isinstance(q_value, Sequence):
            raise TypeError("Analysis data 'Q' must be a numpy array or a sequence of arrays.")
        q_arrays = tuple(np.asarray(q_component, dtype=float).reshape(-1) for q_component in q_value)
        if len(q_arrays) == 0:
            raise ValueError("Analysis data 'Q' must contain at least one Q array.")

    return OptimizerInput(
        q=q_arrays,
        i=np.asarray(analysis_data["I"], dtype=float).reshape(-1),
        isigma=np.asarray(analysis_data["ISigma"], dtype=float).reshape(-1),
    )


def optimizer_input_from_bundle(bundle: Mapping[str, Any]) -> OptimizerInput:
    """Build normalized optimizer arrays from a canonical bundle."""

    return optimizer_input_from_analysis_data(analysis_data_from_bundle(bundle))


def as_optimizer_input(data: Any) -> OptimizerInput:
    """Coerce supported analysis inputs into an `OptimizerInput` instance."""

    if isinstance(data, OptimizerInput):
        return data

    if isinstance(data, Mapping):
        if "signal" in data:
            return optimizer_input_from_bundle(data)
        if {"Q", "I", "ISigma"}.issubset(data.keys()):
            return optimizer_input_from_analysis_data(data)

    raise TypeError("Optimizer input must be an OptimizerInput, a canonical DataBundle, or an analysis-data dict.")


__all__ = [
    "OptimizerInput",
    "as_optimizer_input",
    "optimizer_input_from_analysis_data",
    "optimizer_input_from_bundle",
]
