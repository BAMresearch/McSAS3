from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from .data_adapters import legacy_measdata_from_bundle


@dataclass(frozen=True)
class OptimizerInput:
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
        return len(self.q)

    @property
    def q_for_model(self) -> list[np.ndarray]:
        return [q_component.copy() for q_component in self.q]

    @property
    def primary_q(self) -> np.ndarray:
        return self.q[0]

    @property
    def q_support(self) -> np.ndarray:
        if self.ndim == 1:
            return np.abs(self.primary_q)
        return np.sqrt(np.sum(np.stack([q_component**2 for q_component in self.q], axis=0), axis=0))

    def to_legacy_measdata(self) -> dict[str, list[np.ndarray] | np.ndarray]:
        return {
            "Q": [q_component.copy() for q_component in self.q],
            "I": self.i.copy(),
            "ISigma": self.isigma.copy(),
        }


def optimizer_input_from_legacy_measdata(measdata: Mapping[str, Any]) -> OptimizerInput:
    required_keys = {"Q", "I", "ISigma"}
    missing_keys = required_keys.difference(measdata.keys())
    if missing_keys:
        raise KeyError(f"Legacy measurement data is missing required keys: {sorted(missing_keys)}")

    q_value = measdata["Q"]
    if isinstance(q_value, np.ndarray):
        q_arrays = (np.asarray(q_value, dtype=float).reshape(-1),)
    else:
        q_arrays = tuple(np.asarray(q_component, dtype=float).reshape(-1) for q_component in q_value)

    return OptimizerInput(
        q=q_arrays,
        i=np.asarray(measdata["I"], dtype=float).reshape(-1),
        isigma=np.asarray(measdata["ISigma"], dtype=float).reshape(-1),
    )


def optimizer_input_from_bundle(bundle: Mapping[str, Any], *, q_nudge: Any = None) -> OptimizerInput:
    return optimizer_input_from_legacy_measdata(legacy_measdata_from_bundle(bundle, q_nudge=q_nudge))


def as_optimizer_input(data: Any, *, q_nudge: Any = None) -> OptimizerInput:
    if isinstance(data, OptimizerInput):
        return data

    if isinstance(data, Mapping):
        if "signal" in data:
            return optimizer_input_from_bundle(data, q_nudge=q_nudge)
        if {"Q", "I", "ISigma"}.issubset(data.keys()):
            return optimizer_input_from_legacy_measdata(data)

    raise TypeError("Optimizer input must be an OptimizerInput, a canonical DataBundle, or a legacy measurement dict.")


__all__ = [
    "OptimizerInput",
    "as_optimizer_input",
    "optimizer_input_from_bundle",
    "optimizer_input_from_legacy_measdata",
]
