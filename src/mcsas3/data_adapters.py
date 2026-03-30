from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

import numpy as np
import pandas

from .data_model import BaseData, DataBundle, ProcessingData, ureg

STAGE_RAW = "sample_raw"
STAGE_CLIPPED = "sample_clipped"
STAGE_BINNED = "sample_binned"
CANONICAL_STAGE_NAMES = (STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED)
DEFAULT_ANALYSIS_STAGE = STAGE_BINNED
ANALYSIS_STAGE_ATTRIBUTE = "analysis_stage"
CANONICAL_1D_KEYS = ("signal", "Q", "mask")
CANONICAL_2D_KEYS = ("signal", "Qx", "Qy", "mask")

DEFAULT_Q_UNITS = ureg.Unit("1 / nanometer")
DEFAULT_INTENSITY_UNITS = ureg.Unit("1 / meter / steradian")
DEFAULT_UNCERTAINTY_KEY = "propagate_to_all"
CanonicalBundleLike: TypeAlias = Mapping[str, BaseData]
AnalysisDataDict: TypeAlias = dict[str, list[np.ndarray] | np.ndarray]


def _require_supported_rank(signal: np.ndarray) -> None:
    if signal.ndim not in (1, 2):
        raise ValueError(f"Canonical scattering bundles must be 1D or 2D, got rank {signal.ndim}.")
    if signal.size == 0:
        raise ValueError("Canonical scattering bundles cannot be empty.")


def _require_matching_shape(name: str, array: np.ndarray, expected_shape: Sequence[int]) -> None:
    if array.shape != tuple(expected_shape):
        raise ValueError(f"{name} shape {array.shape} does not match signal shape {tuple(expected_shape)}.")


def _resolve_unit(unit_value: Any, *, default) -> Any:
    if unit_value is None:
        return default
    if isinstance(unit_value, str):
        normalized = unit_value.strip()
        reciprocal_angstrom_aliases = {
            "1/A": "1 / angstrom",
            "A^-1": "1 / angstrom",
            "Å^-1": "1 / angstrom",
            "1/Å": "1 / angstrom",
        }
        if normalized in reciprocal_angstrom_aliases:
            unit_value = reciprocal_angstrom_aliases[normalized]
    return ureg.Unit(unit_value)


def _as_array(data: Any, *, dtype: Any = float) -> np.ndarray:
    return np.asarray(data, dtype=dtype)


def _combine_uncertainties(data: BaseData) -> np.ndarray:
    if not data.uncertainties:
        raise ValueError("Legacy conversion requires at least one uncertainty array.")

    variance = np.zeros_like(_as_array(data.signal, dtype=float), dtype=float)
    for uncertainty in data.uncertainties.values():
        variance += _as_array(uncertainty, dtype=float) ** 2
    return np.sqrt(variance)


def _optional_uncertainties(signal: Any) -> dict[str, np.ndarray]:
    if signal is None:
        return {}
    return {DEFAULT_UNCERTAINTY_KEY: np.array(signal, dtype=float, copy=True)}


def _normalize_bundle_units(
    bundle: DataBundle,
    *,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
) -> DataBundle:
    target_q_units = _resolve_unit(q_units, default=DEFAULT_Q_UNITS)
    target_intensity_units = _resolve_unit(intensity_units, default=DEFAULT_INTENSITY_UNITS)

    bundle["signal"].to_units(target_intensity_units)
    if "Q" in bundle:
        bundle["Q"].to_units(target_q_units)
    if "Qx" in bundle:
        bundle["Qx"].to_units(target_q_units)
    if "Qy" in bundle:
        bundle["Qy"].to_units(target_q_units)
    return bundle


def _stage_bundle(
    *,
    signal: Any,
    signal_uncertainty: Any,
    q0: Any,
    q1: Any | None = None,
    q_uncertainty: Any = None,
    mask: Any = None,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
    source_q_units=None,
    source_intensity_units=None,
) -> DataBundle:
    bundle = DataBundle()
    signal_array = np.array(signal, dtype=float, copy=True)
    _require_supported_rank(signal_array)
    rank_of_data = signal_array.ndim
    signal_uncertainty_array = None
    if signal_uncertainty is not None:
        signal_uncertainty_array = np.array(signal_uncertainty, dtype=float, copy=True)
        _require_matching_shape("signal_uncertainty", signal_uncertainty_array, signal_array.shape)
    q0_array = np.array(q0, dtype=float, copy=True)
    _require_matching_shape("q0", q0_array, signal_array.shape)
    q1_array = None
    if q1 is not None:
        q1_array = np.array(q1, dtype=float, copy=True)
        _require_matching_shape("q1", q1_array, signal_array.shape)
    q_uncertainty_array = None
    if q_uncertainty is not None:
        q_uncertainty_array = np.array(q_uncertainty, dtype=float, copy=True)
        _require_matching_shape("q_uncertainty", q_uncertainty_array, signal_array.shape)
    mask_array = None
    if mask is not None:
        mask_array = np.array(mask, dtype=bool, copy=True)
        _require_matching_shape("mask", mask_array, signal_array.shape)
    source_q_units = _resolve_unit(source_q_units, default=_resolve_unit(q_units, default=DEFAULT_Q_UNITS))
    source_intensity_units = _resolve_unit(
        source_intensity_units,
        default=_resolve_unit(intensity_units, default=DEFAULT_INTENSITY_UNITS),
    )
    bundle["signal"] = BaseData(
        signal=signal_array,
        units=source_intensity_units,
        uncertainties=_optional_uncertainties(signal_uncertainty_array),
        rank_of_data=rank_of_data,
    )
    if q1 is None:
        bundle["Q"] = BaseData(
            signal=q0_array,
            units=source_q_units,
            uncertainties=_optional_uncertainties(q_uncertainty_array),
            rank_of_data=rank_of_data,
        )
    else:
        bundle["Qy"] = BaseData(
            signal=q0_array,
            units=source_q_units,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
        bundle["Qx"] = BaseData(
            signal=q1_array,
            units=source_q_units,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
    if mask_array is not None:
        bundle["mask"] = BaseData(
            signal=mask_array,
            units=ureg.dimensionless,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
    bundle.default_plot = "signal"
    return _normalize_bundle_units(bundle, q_units=q_units, intensity_units=intensity_units)


def bundle_from_1d_dataframe(
    df: pandas.DataFrame,
    *,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
    source_q_units=None,
    source_intensity_units=None,
) -> DataBundle:
    """Build a canonical 1D bundle from a dataframe in source or canonical units."""

    required_columns = {"Q", "I", "ISigma"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise KeyError(f"1D dataframe is missing required columns: {sorted(missing_columns)}")

    return _stage_bundle(
        signal=df["I"].to_numpy(dtype=float),
        signal_uncertainty=df["ISigma"].to_numpy(dtype=float),
        q0=df["Q"].to_numpy(dtype=float),
        q_uncertainty=df["QSigma"].to_numpy(dtype=float) if "QSigma" in df.columns else None,
        mask=df["mask"].to_numpy(dtype=bool) if "mask" in df.columns else None,
        q_units=q_units,
        intensity_units=intensity_units,
        source_q_units=source_q_units,
        source_intensity_units=source_intensity_units,
    )


def bundle_from_2d_arrays(
    *,
    intensity: Any,
    intensity_sigma: Any,
    qx: Any,
    qy: Any,
    mask: Any = None,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
    source_q_units=None,
    source_intensity_units=None,
) -> DataBundle:
    """Build a canonical 2D bundle from raw array components."""

    return _stage_bundle(
        signal=intensity,
        signal_uncertainty=intensity_sigma,
        q0=qy,
        q1=qx,
        mask=mask,
        q_units=q_units,
        intensity_units=intensity_units,
        source_q_units=source_q_units,
        source_intensity_units=source_intensity_units,
    )


def bundle_from_2d_stage(
    stage_data: Mapping[str, Any],
    *,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
    source_q_units=None,
    source_intensity_units=None,
) -> DataBundle:
    """Build a canonical 2D bundle from raw or clipped legacy-style stage mappings."""

    raw_keys = {"I", "ISigma", "Qx", "Qy"}
    clipped_keys = {"I2D", "ISigma2D", "Q0Crop2D", "Q1Crop2D"}

    if raw_keys.issubset(stage_data):
        return bundle_from_2d_arrays(
            intensity=stage_data["I"],
            intensity_sigma=stage_data["ISigma"],
            qx=stage_data["Qx"],
            qy=stage_data["Qy"],
            mask=stage_data.get("mask"),
            q_units=q_units,
            intensity_units=intensity_units,
            source_q_units=source_q_units,
            source_intensity_units=source_intensity_units,
        )
    if clipped_keys.issubset(stage_data):
        return bundle_from_2d_arrays(
            intensity=stage_data["I2D"],
            intensity_sigma=stage_data["ISigma2D"],
            qx=stage_data["Q1Crop2D"],
            qy=stage_data["Q0Crop2D"],
            mask=stage_data.get("mask2D"),
            q_units=q_units,
            intensity_units=intensity_units,
            source_q_units=source_q_units,
            source_intensity_units=source_intensity_units,
        )
    raise KeyError(
        "2D stage data must provide either raw keys "
        "('I', 'ISigma', 'Qx', 'Qy') or clipped keys ('I2D', 'ISigma2D', 'Q0Crop2D', 'Q1Crop2D')."
    )


def normalize_analysis_stage(stage_name: str) -> str:
    """Validate and normalize the selected analysis stage name."""

    if stage_name not in CANONICAL_STAGE_NAMES:
        raise ValueError(f"Invalid analysis stage '{stage_name}'. Expected one of: {', '.join(CANONICAL_STAGE_NAMES)}.")
    return stage_name


def set_processing_analysis_stage(processing: ProcessingData, stage_name: str) -> ProcessingData:
    """Store the selected analysis stage on a `ProcessingData` carrier."""

    normalized_stage = normalize_analysis_stage(stage_name)
    setattr(processing, ANALYSIS_STAGE_ATTRIBUTE, normalized_stage)
    return processing


def get_processing_analysis_stage(
    processing: ProcessingData,
    *,
    default: str = DEFAULT_ANALYSIS_STAGE,
) -> str:
    """Read the selected analysis stage from a `ProcessingData` carrier."""

    stage_name = getattr(processing, ANALYSIS_STAGE_ATTRIBUTE, default)
    return normalize_analysis_stage(stage_name)


def selected_bundle_from_processing(
    processing: ProcessingData,
    *,
    stage_name: str | None = None,
) -> DataBundle:
    """Return the selected canonical stage bundle from a processing carrier."""

    if stage_name is None:
        resolved_stage = get_processing_analysis_stage(processing)
    else:
        resolved_stage = normalize_analysis_stage(stage_name)
    if resolved_stage not in processing:
        raise KeyError(f"Selected analysis stage '{resolved_stage}' is not available in the supplied ProcessingData.")
    return processing[resolved_stage]


def is_canonical_bundle(data: Any) -> bool:
    """Return whether the object matches the canonical 1D or 2D bundle contract."""

    return isinstance(data, Mapping) and "signal" in data and ("Q" in data or {"Qx", "Qy"}.issubset(data.keys()))


def as_analysis_bundle(data: Any) -> DataBundle:
    """Coerce a processing carrier or bundle into the selected canonical bundle."""

    if isinstance(data, ProcessingData):
        return selected_bundle_from_processing(data)
    if is_canonical_bundle(data):
        return data
    raise TypeError("Analysis input must be a canonical DataBundle or a ProcessingData carrier.")


def bundle_dimension(bundle: CanonicalBundleLike) -> int:
    """Return the scattering dimensionality encoded by a canonical bundle."""

    if {"signal", "Q"}.issubset(bundle):
        return 1
    if {"signal", "Qx", "Qy"}.issubset(bundle):
        return 2
    raise ValueError("Bundle does not match the canonical 1D or 2D scattering contract.")


def fit_arrays_from_bundle(bundle: CanonicalBundleLike) -> tuple[tuple[np.ndarray, ...], np.ndarray, np.ndarray]:
    """Flatten a canonical bundle into the Q, intensity, and sigma arrays used for fitting."""

    ndim = bundle_dimension(bundle)
    signal = _as_array(bundle["signal"].signal, dtype=float)
    signal_sigma = _combine_uncertainties(bundle["signal"])

    if ndim == 1:
        q = _as_array(bundle["Q"].signal, dtype=float).reshape(-1)
        return (q,), signal.reshape(-1), signal_sigma.reshape(-1)

    qy = _as_array(bundle["Qy"].signal, dtype=float)
    qx = _as_array(bundle["Qx"].signal, dtype=float)
    mask = np.zeros_like(signal, dtype=bool)
    if "mask" in bundle:
        mask = _as_array(bundle["mask"].signal, dtype=bool)

    valid = np.isfinite(signal) & np.isfinite(signal_sigma) & (signal_sigma != 0) & np.invert(mask)
    return (
        (
            qy[valid].flatten(),
            qx[valid].flatten(),
        ),
        signal[valid].flatten(),
        signal_sigma[valid].flatten(),
    )


def model_q_arrays_from_bundle(bundle: CanonicalBundleLike) -> list[np.ndarray]:
    """Return Q arrays in the shape expected by SasModels kernels."""

    q_arrays, _signal, _signal_sigma = fit_arrays_from_bundle(bundle)
    return [q_component.copy() for q_component in q_arrays]


def q_support_from_bundle(bundle: CanonicalBundleLike) -> np.ndarray:
    """Return absolute Q support for limit auto-scaling."""

    q_arrays, _signal, _signal_sigma = fit_arrays_from_bundle(bundle)
    if len(q_arrays) == 1:
        return np.abs(q_arrays[0])
    return np.sqrt(np.sum(np.stack([q_component**2 for q_component in q_arrays], axis=0), axis=0))


def analysis_data_from_bundle(bundle: CanonicalBundleLike) -> AnalysisDataDict:
    """Build the flat analysis-data dict used by remaining legacy-adjacent paths."""

    ndim = bundle_dimension(bundle)
    signal = _as_array(bundle["signal"].signal, dtype=float)
    signal_sigma = _combine_uncertainties(bundle["signal"])

    if ndim == 1:
        q = _as_array(bundle["Q"].signal, dtype=float)
        return {"Q": [q], "I": signal.copy(), "ISigma": signal_sigma}

    qy = _as_array(bundle["Qy"].signal, dtype=float)
    qx = _as_array(bundle["Qx"].signal, dtype=float)
    mask = np.zeros_like(signal, dtype=bool)
    if "mask" in bundle:
        mask = _as_array(bundle["mask"].signal, dtype=bool)

    valid = np.isfinite(signal) & np.isfinite(signal_sigma) & (signal_sigma != 0) & np.invert(mask)
    return {
        "Q": [
            qy[valid].flatten(),
            qx[valid].flatten(),
        ],
        "I": signal[valid].flatten(),
        "ISigma": signal_sigma[valid].flatten(),
    }


def frame_from_bundle(bundle: CanonicalBundleLike) -> pandas.DataFrame:
    """Project a canonical bundle into the stage dataframe representation."""

    ndim = bundle_dimension(bundle)
    signal = _as_array(bundle["signal"].signal, dtype=float)
    signal_sigma = _combine_uncertainties(bundle["signal"])

    if ndim == 1:
        frame = pandas.DataFrame(
            {
                "Q": _as_array(bundle["Q"].signal, dtype=float),
                "I": signal,
                "ISigma": signal_sigma,
            }
        )
        if bundle["Q"].uncertainties:
            frame["QSigma"] = _combine_uncertainties(bundle["Q"])
        if "mask" in bundle:
            frame["mask"] = _as_array(bundle["mask"].signal, dtype=bool)
        return frame

    frame = pandas.DataFrame(
        {
            "Qx": _as_array(bundle["Qx"].signal, dtype=float).flatten(),
            "Qy": _as_array(bundle["Qy"].signal, dtype=float).flatten(),
            "I": signal.flatten(),
            "ISigma": signal_sigma.flatten(),
        }
    )
    if "mask" in bundle:
        frame["mask"] = _as_array(bundle["mask"].signal, dtype=bool).flatten()
    return frame


def raw_2d_stage_from_bundle(bundle: CanonicalBundleLike) -> dict[str, np.ndarray]:
    """Project a canonical 2D bundle into the raw-stage array mapping."""

    ndim = bundle_dimension(bundle)
    if ndim != 2:
        raise ValueError("raw_2d_stage_from_bundle requires a canonical 2D scattering bundle.")

    raw_stage = {
        "Qx": _as_array(bundle["Qx"].signal, dtype=float).copy(),
        "Qy": _as_array(bundle["Qy"].signal, dtype=float).copy(),
        "I": _as_array(bundle["signal"].signal, dtype=float).copy(),
        "ISigma": _combine_uncertainties(bundle["signal"]).copy(),
    }
    if "mask" in bundle:
        raw_stage["mask"] = _as_array(bundle["mask"].signal, dtype=bool).copy()
    return raw_stage


__all__ = [
    "ANALYSIS_STAGE_ATTRIBUTE",
    "CANONICAL_1D_KEYS",
    "CANONICAL_2D_KEYS",
    "CANONICAL_STAGE_NAMES",
    "DEFAULT_ANALYSIS_STAGE",
    "DEFAULT_INTENSITY_UNITS",
    "DEFAULT_Q_UNITS",
    "DEFAULT_UNCERTAINTY_KEY",
    "STAGE_BINNED",
    "STAGE_CLIPPED",
    "STAGE_RAW",
    "as_analysis_bundle",
    "bundle_dimension",
    "bundle_from_1d_dataframe",
    "bundle_from_2d_arrays",
    "bundle_from_2d_stage",
    "fit_arrays_from_bundle",
    "get_processing_analysis_stage",
    "is_canonical_bundle",
    "analysis_data_from_bundle",
    "frame_from_bundle",
    "model_q_arrays_from_bundle",
    "normalize_analysis_stage",
    "q_support_from_bundle",
    "raw_2d_stage_from_bundle",
    "selected_bundle_from_processing",
    "set_processing_analysis_stage",
]
