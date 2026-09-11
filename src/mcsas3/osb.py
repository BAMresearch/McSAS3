from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
import scipy.optimize

from .data_adapters import as_analysis_bundle
from .optimizer_input import as_optimizer_input

FIT_SCALE_INDEX = 0
FIT_BACKGROUND_INDEX = 1
FIT_POROD_COEFFICIENT_INDEX = 2
LEGACY_FIT_PARAMETER_NAMES = ("scale", "background")
POROD_FIT_PARAMETER_NAMES = (*LEGACY_FIT_PARAMETER_NAMES, "porodCoefficient")
FlatBackgroundMode = bool | Literal["positive"]


def normalize_flat_background_mode(value: Any) -> FlatBackgroundMode:
    """Return a validated flat-background fitting mode."""

    if isinstance(value, np.bool_):
        value = bool(value)
    if isinstance(value, (bytes, bytearray, np.bytes_)):
        value = value.decode()
    if value is True or value is False or value == "positive":
        return value
    raise ValueError("fitFlatBackground must be true, 'positive', or false.")


def _coerce_measurement_arrays(
    measurement_input: Any,
    measurement_sigma: np.ndarray | Sequence[float] | None,
) -> tuple[np.ndarray | None, np.ndarray, np.ndarray]:
    q_support = None
    if measurement_sigma is None and not isinstance(measurement_input, (np.ndarray, list, tuple)):
        try:
            analysis_bundle = as_analysis_bundle(measurement_input)
        except TypeError:
            optimizer_input = as_optimizer_input(measurement_input)
        else:
            optimizer_input = as_optimizer_input(analysis_bundle)
        q_support = optimizer_input.q_support
        measurement_input = optimizer_input.i
        measurement_sigma = optimizer_input.isigma

    return q_support, np.asarray(measurement_input, dtype=float), np.asarray(measurement_sigma, dtype=float)


def _default_x_bounds(
    measured_intensity: np.ndarray,
    fit_porod_background: bool = False,
    fit_flat_background: FlatBackgroundMode = True,
) -> list[list[float | None]]:
    finite_values = measured_intensity[np.isfinite(measured_intensity)]
    mean_magnitude = abs(float(finite_values.mean()))
    flat_bounds: list[float | None]
    if fit_flat_background is False:
        flat_bounds = [0, 0]
    elif fit_flat_background == "positive":
        flat_bounds = [0, None]
    else:
        flat_bounds = [-mean_magnitude, mean_magnitude]
    bounds: list[list[float | None]] = [[0, None], flat_bounds]
    if fit_porod_background:
        bounds.append([0, None])
    return bounds


def _as_q_support(measurement_q: np.ndarray | Sequence[float] | Sequence[np.ndarray]) -> np.ndarray:
    q_arrays = np.asarray(measurement_q, dtype=float)
    if q_arrays.ndim == 1:
        return np.abs(q_arrays)
    if q_arrays.ndim == 2 and q_arrays.shape[0] == 1:
        return np.abs(q_arrays[0])
    if q_arrays.ndim == 2 and q_arrays.shape[0] == 2:
        return np.sqrt(np.sum(q_arrays**2, axis=0))
    raise ValueError("Measurement Q must contain one 1D Q array or two equally shaped Q component arrays.")


def fit_parameter_names(fit_parameters: Sequence[float]) -> tuple[str, ...]:
    """Return stable names for a supported base-fit parameter vector."""

    parameter_count = np.asarray(fit_parameters).size
    if parameter_count == len(LEGACY_FIT_PARAMETER_NAMES):
        return LEGACY_FIT_PARAMETER_NAMES
    if parameter_count == len(POROD_FIT_PARAMETER_NAMES):
        return POROD_FIT_PARAMETER_NAMES
    raise ValueError(f"Expected two or three base-fit parameters, received {parameter_count}.")


def fitted_intensity(
    model_intensity: np.ndarray | Sequence[float],
    fit_parameters: np.ndarray | Sequence[float],
    q_support: np.ndarray | Sequence[float] | None = None,
) -> np.ndarray:
    """Apply stored scale, flat background, and optional Porod coefficient to a model curve."""

    model_array = np.asarray(model_intensity, dtype=float)
    parameters = np.asarray(fit_parameters, dtype=float).reshape(-1)
    parameter_names = fit_parameter_names(parameters)
    result = parameters[FIT_SCALE_INDEX] * model_array + parameters[FIT_BACKGROUND_INDEX]
    if parameter_names == POROD_FIT_PARAMETER_NAMES:
        if q_support is None:
            raise ValueError("Q support is required to reconstruct a Porod-enabled fitted intensity.")
        q_array = np.asarray(q_support, dtype=float)
        if q_array.shape != model_array.shape:
            raise ValueError("Q support and model intensity must have matching shapes.")
        if np.any(~np.isfinite(q_array)) or np.any(q_array <= 0):
            raise ValueError("Porod background fitting requires finite, strictly positive Q magnitudes.")
        result = result + parameters[FIT_POROD_COEFFICIENT_INDEX] * q_array**-4
    return result


def background_intensity(
    fit_parameters: np.ndarray | Sequence[float],
    q_support: np.ndarray | Sequence[float],
) -> np.ndarray:
    """Return the fitted flat plus optional Porod background contribution."""

    q_array = np.asarray(q_support, dtype=float)
    return fitted_intensity(np.zeros_like(q_array), fit_parameters, q_array)


class optimizeScalingAndBackground:
    """Optimize curve scaling and background against measured intensities."""

    @classmethod
    def from_input(
        cls,
        measurement_input: Any,
        measurement_sigma: np.ndarray | Sequence[float] | None = None,
        xBounds=None,
        fitPorodBackground: bool = False,
        measurement_q: np.ndarray | Sequence[float] | Sequence[np.ndarray] | None = None,
        fitFlatBackground: FlatBackgroundMode = True,
    ) -> "optimizeScalingAndBackground":
        """Construct an optimizer from canonical, optimizer-input, or raw array measurements."""

        return cls(
            measurement_input,
            measurement_sigma,
            xBounds=xBounds,
            fitPorodBackground=fitPorodBackground,
            fitFlatBackground=fitFlatBackground,
            measDataQ=measurement_q,
        )

    def __init__(
        self,
        measDataI=None,
        measDataISigma=None,
        xBounds=None,
        fitPorodBackground: bool = False,
        measDataQ=None,
        fitFlatBackground: FlatBackgroundMode = True,
    ):
        """Initialize scaling/background optimization against flattened intensity data."""

        if not isinstance(fitPorodBackground, bool):
            raise TypeError("fitPorodBackground must be a boolean.")
        fitFlatBackground = normalize_flat_background_mode(fitFlatBackground)
        inferred_q_support, measured_intensity, measured_sigma = _coerce_measurement_arrays(
            measDataI,
            measDataISigma,
        )
        self.measDataI = measured_intensity
        self.measDataISigma = measured_sigma
        self.fitPorodBackground = fitPorodBackground
        self.fitFlatBackground = fitFlatBackground
        self.qSupport = inferred_q_support if measDataQ is None else _as_q_support(measDataQ)
        self.parameterNames = POROD_FIT_PARAMETER_NAMES if fitPorodBackground else LEGACY_FIT_PARAMETER_NAMES
        self.validate()
        self.xBounds = (
            _default_x_bounds(
                self.measDataI,
                fit_porod_background=fitPorodBackground,
                fit_flat_background=fitFlatBackground,
            )
            if xBounds is None
            else [list(bound) for bound in xBounds]
        )
        if len(self.xBounds) != len(self.parameterNames):
            raise ValueError(f"Expected {len(self.parameterNames)} base-fit bounds, received {len(self.xBounds)}.")
        if fitFlatBackground is False:
            self.xBounds[FIT_BACKGROUND_INDEX] = [0, 0]
        elif fitFlatBackground == "positive":
            lower_bound, upper_bound = self.xBounds[FIT_BACKGROUND_INDEX]
            lower_bound = 0 if lower_bound is None else max(0, lower_bound)
            if upper_bound is not None and upper_bound < lower_bound:
                raise ValueError("Flat-background upper bound must be zero or positive in 'positive' mode.")
            self.xBounds[FIT_BACKGROUND_INDEX] = [lower_bound, upper_bound]
        self._porodQMin = None if not fitPorodBackground else float(np.min(self.qSupport))
        self._porodBasis = None if not fitPorodBackground else (self._porodQMin / self.qSupport) ** 4

    def initialGuess(self, optI):
        """Return a robust initial guess for scale and background."""

        sc = np.median(self.measDataI / optI)
        bgnd = self.measDataI[-int(np.floor(4 * len(self.measDataI) / 5)) :].mean()

        if sc <= 0:
            sc = 1.0
        bgnd = np.clip(bgnd, self.xBounds[1][0], self.xBounds[1][1])
        initial_guess = [sc, bgnd]
        if self.fitPorodBackground:
            initial_guess.append(0.0)
        return np.array(initial_guess)

    def validate(self):
        """Validate the measured intensity arrays before optimization."""

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
        if self.fitPorodBackground:
            if self.qSupport is None:
                raise ValueError("Measurement Q is required when fitPorodBackground is enabled.")
            if self.qSupport.shape != self.measDataI.shape:
                raise ValueError("Measurement Q and intensity arrays must have matching shapes.")
            if np.any(~np.isfinite(self.qSupport)) or np.any(self.qSupport <= 0):
                raise ValueError("Porod background fitting requires finite, strictly positive Q magnitudes.")

    @staticmethod
    def optFunc(sc, measDataI, measDataISigma, modelDataI, porod_basis=None):
        """Return the reduced chi-square for scale/background-adjusted model intensities."""

        fitted = modelDataI * sc[FIT_SCALE_INDEX] + sc[FIT_BACKGROUND_INDEX]
        if porod_basis is not None:
            fitted = fitted + sc[FIT_POROD_COEFFICIENT_INDEX] * porod_basis
        cs = np.sum(((measDataI - fitted) / measDataISigma) ** 2) / measDataI.size
        return cs

    def _to_internal_parameters(self, parameters: np.ndarray | Sequence[float]) -> np.ndarray:
        internal = np.asarray(parameters, dtype=float).copy()
        if self.fitPorodBackground:
            internal[FIT_POROD_COEFFICIENT_INDEX] /= self._porodQMin**4
        return internal

    def _to_external_parameters(self, parameters: np.ndarray | Sequence[float]) -> np.ndarray:
        external = np.asarray(parameters, dtype=float).copy()
        if self.fitPorodBackground:
            external[FIT_POROD_COEFFICIENT_INDEX] *= self._porodQMin**4
        return external

    def _internal_bounds(self) -> list[list[float | None]]:
        bounds = [list(bound) for bound in self.xBounds]
        if self.fitPorodBackground:
            bounds[FIT_POROD_COEFFICIENT_INDEX] = [
                None if value is None else value / self._porodQMin**4 for value in bounds[FIT_POROD_COEFFICIENT_INDEX]
            ]
        return bounds

    def _match_linear(self, model_data_i: np.ndarray) -> tuple[np.ndarray, float]:
        predictors = [model_data_i]
        active_parameter_indices = [FIT_SCALE_INDEX]
        if self.fitFlatBackground is not False:
            predictors.append(np.ones_like(model_data_i))
            active_parameter_indices.append(FIT_BACKGROUND_INDEX)
        if self.fitPorodBackground:
            predictors.append(self._porodBasis)
            active_parameter_indices.append(FIT_POROD_COEFFICIENT_INDEX)
        weighted_design = np.column_stack(predictors) / self.measDataISigma[:, np.newaxis]
        weighted_measurement = self.measDataI / self.measDataISigma
        internal_bounds = self._internal_bounds()
        lower_bounds = np.array(
            [
                -np.inf if internal_bounds[index][0] is None else internal_bounds[index][0]
                for index in active_parameter_indices
            ],
            dtype=float,
        )
        upper_bounds = np.array(
            [
                np.inf if internal_bounds[index][1] is None else internal_bounds[index][1]
                for index in active_parameter_indices
            ],
            dtype=float,
        )
        opt = scipy.optimize.lsq_linear(
            weighted_design,
            weighted_measurement,
            bounds=(lower_bounds, upper_bounds),
        )
        if not opt.success:
            raise RuntimeError(f"Scale/background least-squares optimization failed: {opt.message}")
        gof = np.sum(opt.fun**2) / self.measDataI.size
        internal_parameters = np.zeros(len(self.parameterNames), dtype=float)
        internal_parameters[active_parameter_indices] = opt.x
        return self._to_external_parameters(internal_parameters), gof

    def _match_porod(self, model_data_i: np.ndarray) -> tuple[np.ndarray, float]:
        """Retain the previous private Porod-fit entry point for compatibility."""

        return self._match_linear(model_data_i)

    def match(self, modelDataI, x0=None):
        """Optimize scale and background against a model intensity vector."""

        if x0 is None:
            x0 = np.zeros(len(self.parameterNames))
        if np.asarray(x0).size != len(self.parameterNames):
            raise ValueError(
                f"Expected {len(self.parameterNames)} initial fit parameters, received {np.asarray(x0).size}."
            )
        model_data_i = np.asarray(modelDataI, dtype=float)
        if model_data_i.shape != self.measDataI.shape:
            raise ValueError("Model and measured intensity arrays must have matching shapes.")
        return self._match_linear(model_data_i)


__all__ = [
    "FIT_BACKGROUND_INDEX",
    "FIT_POROD_COEFFICIENT_INDEX",
    "FIT_SCALE_INDEX",
    "LEGACY_FIT_PARAMETER_NAMES",
    "POROD_FIT_PARAMETER_NAMES",
    "FlatBackgroundMode",
    "background_intensity",
    "fit_parameter_names",
    "fitted_intensity",
    "normalize_flat_background_mode",
    "optimizeScalingAndBackground",
]
