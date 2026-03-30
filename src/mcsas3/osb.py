from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import scipy.optimize

from .data_adapters import as_analysis_bundle, fit_arrays_from_bundle
from .optimizer_input import as_optimizer_input


def _coerce_measurement_arrays(
    measurement_input: Any,
    measurement_sigma: np.ndarray | Sequence[float] | None,
) -> tuple[np.ndarray, np.ndarray]:
    if measurement_sigma is None and not isinstance(measurement_input, (np.ndarray, list, tuple)):
        try:
            analysis_bundle = as_analysis_bundle(measurement_input)
        except TypeError:
            optimizer_input = as_optimizer_input(measurement_input)
            measurement_input = optimizer_input.i
            measurement_sigma = optimizer_input.isigma
        else:
            _q_arrays, measurement_input, measurement_sigma = fit_arrays_from_bundle(analysis_bundle)

    return np.asarray(measurement_input, dtype=float), np.asarray(measurement_sigma, dtype=float)


def _default_x_bounds(measured_intensity: np.ndarray) -> list[list[float | None]]:
    finite_values = measured_intensity[np.isfinite(measured_intensity)]
    mean_value = float(finite_values.mean())
    return [[0, None], [-mean_value, mean_value]]


class optimizeScalingAndBackground:
    """Optimize curve scaling and background against measured intensities."""

    @classmethod
    def from_input(
        cls,
        measurement_input: Any,
        measurement_sigma: np.ndarray | Sequence[float] | None = None,
        xBounds=None,
    ) -> "optimizeScalingAndBackground":
        measured_intensity, measured_sigma = _coerce_measurement_arrays(measurement_input, measurement_sigma)
        return cls(measured_intensity, measured_sigma, xBounds=xBounds)

    def __init__(self, measDataI=None, measDataISigma=None, xBounds=None):
        measured_intensity, measured_sigma = _coerce_measurement_arrays(measDataI, measDataISigma)
        self.measDataI = measured_intensity
        self.measDataISigma = measured_sigma
        self.validate()
        self.xBounds = _default_x_bounds(self.measDataI) if xBounds is None else xBounds

    def initialGuess(self, optI):
        sc = np.median(self.measDataI / optI)
        bgnd = self.measDataI[-int(np.floor(4 * len(self.measDataI) / 5)) :].mean()

        if sc <= 0:
            sc = 1.0
        bgnd = np.clip(bgnd, self.xBounds[1][0], self.xBounds[1][1])
        return np.array([sc, bgnd])

    def validate(self):
        if np.any(np.isnan(self.measDataI)):
            raise ValueError("Measured intensities cannot contain NaN values.")
        if np.any(np.isinf(self.measDataI)):
            raise ValueError("Measured intensities cannot contain infinite values.")
        if np.any(np.isnan(self.measDataISigma)):
            raise ValueError("Intensity uncertainties cannot contain NaN values.")
        if np.any(np.isinf(self.measDataISigma)):
            raise ValueError("Intensity uncertainties cannot contain infinite values.")
        if not np.any(np.isfinite(self.measDataISigma)):
            raise ValueError("At least one finite intensity uncertainty is required.")
        if self.measDataI.size == 0:
            raise ValueError("Measured intensities cannot be empty.")
        if self.measDataI.shape != self.measDataISigma.shape:
            raise ValueError("Measured intensities and uncertainties must have matching shapes.")
        if self.measDataI.ndim != 1:
            raise ValueError("Measured intensities must be one-dimensional.")

    @staticmethod
    def optFunc(sc, measDataI, measDataISigma, modelDataI):
        cs = np.sum(((measDataI - (modelDataI * sc[0] + sc[1])) / measDataISigma) ** 2) / measDataI.size
        return cs

    def match(self, modelDataI, x0=None):
        if x0 is None:
            x0 = self.initialGuess(modelDataI)
        opt = scipy.optimize.minimize(
            self.optFunc,
            x0,
            args=(self.measDataI, self.measDataISigma, modelDataI),
            method="TNC",
            bounds=self.xBounds,
        )
        return opt["x"], opt["fun"]
