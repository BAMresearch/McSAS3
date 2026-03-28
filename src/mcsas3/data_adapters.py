from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas

from .data_model import BaseData, DataBundle, ProcessingData, ureg

STAGE_RAW = "sample_raw"
STAGE_CLIPPED = "sample_clipped"
STAGE_BINNED = "sample_binned"
CANONICAL_STAGE_NAMES = (STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED)

CANONICAL_1D_KEYS = ("signal", "Q", "mask")
CANONICAL_2D_KEYS = ("signal", "Qx", "Qy", "mask")

DEFAULT_Q_UNITS = ureg.Unit("1 / nanometer")
DEFAULT_INTENSITY_UNITS = ureg.AFU
LEGACY_UNCERTAINTY_KEY = "propagate_to_all"


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
    return {LEGACY_UNCERTAINTY_KEY: _as_array(signal, dtype=float)}


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
) -> DataBundle:
    bundle = DataBundle()
    signal_array = _as_array(signal, dtype=float)
    rank_of_data = signal_array.ndim
    bundle["signal"] = BaseData(
        signal=signal_array,
        units=intensity_units,
        uncertainties=_optional_uncertainties(signal_uncertainty),
        rank_of_data=rank_of_data,
    )
    if q1 is None:
        bundle["Q"] = BaseData(
            signal=_as_array(q0, dtype=float),
            units=q_units,
            uncertainties=_optional_uncertainties(q_uncertainty),
            rank_of_data=rank_of_data,
        )
    else:
        bundle["Qy"] = BaseData(
            signal=_as_array(q0, dtype=float),
            units=q_units,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
        bundle["Qx"] = BaseData(
            signal=_as_array(q1, dtype=float),
            units=q_units,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
    if mask is not None:
        bundle["mask"] = BaseData(
            signal=_as_array(mask, dtype=bool),
            units=ureg.dimensionless,
            uncertainties={},
            rank_of_data=rank_of_data,
        )
    bundle.default_plot = "signal"
    return bundle


def bundle_from_1d_dataframe(
    df: pandas.DataFrame,
    *,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
) -> DataBundle:
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
) -> DataBundle:
    return _stage_bundle(
        signal=intensity,
        signal_uncertainty=intensity_sigma,
        q0=qy,
        q1=qx,
        mask=mask,
        q_units=q_units,
        intensity_units=intensity_units,
    )


def bundle_from_2d_stage(
    stage_data: Mapping[str, Any],
    *,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
) -> DataBundle:
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
        )
    raise KeyError(
        "2D stage data must provide either raw keys "
        "('I', 'ISigma', 'Qx', 'Qy') or clipped keys ('I2D', 'ISigma2D', 'Q0Crop2D', 'Q1Crop2D')."
    )


def bundle_from_legacy_stage(
    stage_data: Any,
    *,
    is_2d: bool | None = None,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
) -> DataBundle:
    if isinstance(stage_data, pandas.DataFrame):
        if is_2d:
            raise TypeError("2D stage data must be provided as the native dict-of-arrays form, not a dataframe.")
        return bundle_from_1d_dataframe(stage_data, q_units=q_units, intensity_units=intensity_units)

    if isinstance(stage_data, Mapping):
        if is_2d is False:
            raise TypeError("1D stage data must be provided as a dataframe, not a dict-of-arrays.")
        return bundle_from_2d_stage(stage_data, q_units=q_units, intensity_units=intensity_units)

    raise TypeError(f"Unsupported legacy stage type: {type(stage_data).__name__}")


def processing_from_legacy_stages(
    *,
    raw_data: Any = None,
    clipped_data: Any = None,
    binned_data: Any = None,
    is_2d: bool | None = None,
    q_units=DEFAULT_Q_UNITS,
    intensity_units=DEFAULT_INTENSITY_UNITS,
) -> ProcessingData:
    processing = ProcessingData()
    for stage_name, stage_data in (
        (STAGE_RAW, raw_data),
        (STAGE_CLIPPED, clipped_data),
        (STAGE_BINNED, binned_data),
    ):
        if stage_data is None:
            continue
        processing[stage_name] = bundle_from_legacy_stage(
            stage_data,
            is_2d=is_2d,
            q_units=q_units,
            intensity_units=intensity_units,
        )
    return processing


def bundle_dimension(bundle: Mapping[str, BaseData]) -> int:
    if {"signal", "Q"}.issubset(bundle):
        return 1
    if {"signal", "Qx", "Qy"}.issubset(bundle):
        return 2
    raise ValueError("Bundle does not match the canonical 1D or 2D scattering contract.")


def _normalized_q_nudge(q_nudge: Any, *, ndim: int) -> tuple[float, ...]:
    if ndim == 1:
        if q_nudge is None:
            return (0.0,)
        return (float(q_nudge),)

    if q_nudge is None:
        return (0.0, 0.0)
    if np.isscalar(q_nudge):
        return (float(q_nudge), 0.0)

    q_nudge = tuple(float(value) for value in q_nudge)
    if len(q_nudge) != 2:
        raise ValueError("2D q_nudge must contain exactly two offsets.")
    return q_nudge


def legacy_measdata_from_bundle(bundle: Mapping[str, BaseData], *, q_nudge: Any = None) -> dict[str, list | np.ndarray]:
    ndim = bundle_dimension(bundle)
    q_offsets = _normalized_q_nudge(q_nudge, ndim=ndim)
    signal = _as_array(bundle["signal"].signal, dtype=float)
    signal_sigma = _combine_uncertainties(bundle["signal"])

    if ndim == 1:
        q = _as_array(bundle["Q"].signal, dtype=float) + q_offsets[0]
        return {"Q": [q], "I": signal.copy(), "ISigma": signal_sigma}

    qy = _as_array(bundle["Qy"].signal, dtype=float)
    qx = _as_array(bundle["Qx"].signal, dtype=float)
    mask = np.zeros_like(signal, dtype=bool)
    if "mask" in bundle:
        mask = _as_array(bundle["mask"].signal, dtype=bool)

    valid = np.isfinite(signal) & np.isfinite(signal_sigma) & (signal_sigma != 0) & np.invert(mask)
    return {
        "Q": [
            qy[valid].flatten() + q_offsets[0],
            qx[valid].flatten() + q_offsets[1],
        ],
        "I": signal[valid].flatten(),
        "ISigma": signal_sigma[valid].flatten(),
    }


def legacy_dataframe_from_bundle(bundle: Mapping[str, BaseData]) -> pandas.DataFrame:
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


__all__ = [
    "CANONICAL_1D_KEYS",
    "CANONICAL_2D_KEYS",
    "CANONICAL_STAGE_NAMES",
    "DEFAULT_INTENSITY_UNITS",
    "DEFAULT_Q_UNITS",
    "LEGACY_UNCERTAINTY_KEY",
    "STAGE_BINNED",
    "STAGE_CLIPPED",
    "STAGE_RAW",
    "bundle_dimension",
    "bundle_from_1d_dataframe",
    "bundle_from_2d_arrays",
    "bundle_from_2d_stage",
    "bundle_from_legacy_stage",
    "legacy_dataframe_from_bundle",
    "legacy_measdata_from_bundle",
    "processing_from_legacy_stages",
]
