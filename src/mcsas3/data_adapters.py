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
DEFAULT_ANALYSIS_STAGE = STAGE_BINNED
ANALYSIS_STAGE_ATTRIBUTE = "analysis_stage"
LEGACY_LINK_BY_STAGE = {
    STAGE_RAW: "rawData",
    STAGE_CLIPPED: "clippedData",
    STAGE_BINNED: "binnedData",
}
STAGE_BY_LEGACY_LINK = {legacy_link: stage_name for stage_name, legacy_link in LEGACY_LINK_BY_STAGE.items()}

CANONICAL_1D_KEYS = ("signal", "Q", "mask")
CANONICAL_2D_KEYS = ("signal", "Qx", "Qy", "mask")

DEFAULT_Q_UNITS = ureg.Unit("1 / nanometer")
DEFAULT_INTENSITY_UNITS = ureg.Unit("1 / meter / steradian")
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


def normalize_analysis_stage(stage_name: str) -> str:
    if stage_name not in CANONICAL_STAGE_NAMES:
        raise ValueError(f"Invalid analysis stage '{stage_name}'. Expected one of: {', '.join(CANONICAL_STAGE_NAMES)}.")
    return stage_name


def canonical_stage_from_legacy_link(link_name: str) -> str:
    if link_name not in STAGE_BY_LEGACY_LINK:
        raise ValueError(
            f"Invalid legacy stage link '{link_name}'. Expected one of: {', '.join(STAGE_BY_LEGACY_LINK)}."
        )
    return STAGE_BY_LEGACY_LINK[link_name]


def legacy_link_from_canonical_stage(stage_name: str) -> str:
    return LEGACY_LINK_BY_STAGE[normalize_analysis_stage(stage_name)]


def set_processing_analysis_stage(processing: ProcessingData, stage_name: str) -> ProcessingData:
    normalized_stage = normalize_analysis_stage(stage_name)
    setattr(processing, ANALYSIS_STAGE_ATTRIBUTE, normalized_stage)
    return processing


def get_processing_analysis_stage(
    processing: ProcessingData,
    *,
    default: str = DEFAULT_ANALYSIS_STAGE,
) -> str:
    stage_name = getattr(processing, ANALYSIS_STAGE_ATTRIBUTE, default)
    return normalize_analysis_stage(stage_name)


def selected_bundle_from_processing(
    processing: ProcessingData,
    *,
    stage_name: str | None = None,
) -> DataBundle:
    if stage_name is None:
        resolved_stage = get_processing_analysis_stage(processing)
    else:
        resolved_stage = normalize_analysis_stage(stage_name)
    if resolved_stage not in processing:
        raise KeyError(f"Selected analysis stage '{resolved_stage}' is not available in the supplied ProcessingData.")
    return processing[resolved_stage]


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


def legacy_rawdata2d_from_bundle(bundle: Mapping[str, BaseData]) -> dict[str, np.ndarray]:
    ndim = bundle_dimension(bundle)
    if ndim != 2:
        raise ValueError("legacy_rawdata2d_from_bundle requires a canonical 2D scattering bundle.")

    raw_stage = {
        "Qx": _as_array(bundle["Qx"].signal, dtype=float).copy(),
        "Qy": _as_array(bundle["Qy"].signal, dtype=float).copy(),
        "I": _as_array(bundle["signal"].signal, dtype=float).copy(),
        "ISigma": _combine_uncertainties(bundle["signal"]).copy(),
    }
    if "mask" in bundle:
        raw_stage["mask"] = _as_array(bundle["mask"].signal, dtype=bool).copy()
    return raw_stage


def legacy_2d_stage_from_bundle(bundle: Mapping[str, BaseData]) -> dict[str, list | np.ndarray]:
    raw_stage = legacy_rawdata2d_from_bundle(bundle)
    mask = raw_stage.get("mask", np.zeros_like(raw_stage["I"], dtype=bool))
    valid = (
        np.isfinite(raw_stage["I"]) & np.isfinite(raw_stage["ISigma"]) & (raw_stage["ISigma"] != 0) & np.invert(mask)
    )

    stage = {
        "I2D": raw_stage["I"].copy(),
        "mask2D": mask.copy(),
        "ISigma2D": raw_stage["ISigma"].copy(),
        "Q0Crop2D": raw_stage["Qy"].copy(),
        "Q1Crop2D": raw_stage["Qx"].copy(),
        "kansas": raw_stage["I"].shape,
        "invMask": valid.copy(),
        "I": raw_stage["I"][valid].flatten(),
        "ISigma": raw_stage["ISigma"][valid].flatten(),
        "Q": [
            raw_stage["Qy"][valid].flatten(),
            raw_stage["Qx"][valid].flatten(),
        ],
    }
    if stage["I"].size == 0:
        stage["Qextent"] = [np.nan, np.nan, np.nan, np.nan]
    else:
        stage["Qextent"] = [
            stage["Q"][0].min(),
            stage["Q"][0].max(),
            stage["Q"][1].min(),
            stage["Q"][1].max(),
        ]
    return stage


__all__ = [
    "ANALYSIS_STAGE_ATTRIBUTE",
    "CANONICAL_1D_KEYS",
    "CANONICAL_2D_KEYS",
    "CANONICAL_STAGE_NAMES",
    "DEFAULT_ANALYSIS_STAGE",
    "DEFAULT_INTENSITY_UNITS",
    "DEFAULT_Q_UNITS",
    "LEGACY_UNCERTAINTY_KEY",
    "LEGACY_LINK_BY_STAGE",
    "STAGE_BINNED",
    "STAGE_CLIPPED",
    "STAGE_RAW",
    "STAGE_BY_LEGACY_LINK",
    "bundle_dimension",
    "bundle_from_1d_dataframe",
    "bundle_from_2d_arrays",
    "bundle_from_2d_stage",
    "bundle_from_legacy_stage",
    "canonical_stage_from_legacy_link",
    "get_processing_analysis_stage",
    "legacy_2d_stage_from_bundle",
    "legacy_dataframe_from_bundle",
    "legacy_link_from_canonical_stage",
    "legacy_measdata_from_bundle",
    "legacy_rawdata2d_from_bundle",
    "normalize_analysis_stage",
    "processing_from_legacy_stages",
    "selected_bundle_from_processing",
    "set_processing_analysis_stage",
]
