import logging
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

import attrs
import numpy as np
import pandas

from .data_adapters import (
    _combine_uncertainties,
    bundle_dimension,
    bundle_from_1d_dataframe,
    bundle_from_2d_arrays,
    frame_from_bundle,
    raw_2d_stage_from_bundle,
)
from .data_model import BaseData, DataBundle

logger = logging.getLogger(__name__)
RangeLike: TypeAlias = Sequence[float]
RangeListLike: TypeAlias = Sequence[Sequence[float]] | None


@attrs.frozen
class Prepared1DStage:
    """Canonical 1D stage plus its compatibility table view."""

    bundle: DataBundle = attrs.field(validator=attrs.validators.instance_of(DataBundle))
    frame: pandas.DataFrame = attrs.field(validator=attrs.validators.instance_of(pandas.DataFrame))


@attrs.frozen
class Prepared1DResult:
    """Prepared clipped and binned 1D stages."""

    clipped: Prepared1DStage = attrs.field(validator=attrs.validators.instance_of(Prepared1DStage))
    binned: Prepared1DStage = attrs.field(validator=attrs.validators.instance_of(Prepared1DStage))


@attrs.frozen
class Prepared2DResult:
    """Prepared clipped and binned 2D stages."""

    clipped: DataBundle = attrs.field(validator=attrs.validators.instance_of(DataBundle))
    binned: DataBundle = attrs.field(validator=attrs.validators.instance_of(DataBundle))


def _copy_bundle_metadata(source: Mapping[str, BaseData], target: DataBundle) -> DataBundle:
    if getattr(source, "default_plot", None) is not None:
        target.default_plot = source.default_plot
    if getattr(source, "description", None) is not None:
        target.description = source.description
    return target


def copy_bundle(bundle: Mapping[str, BaseData]) -> DataBundle:
    """Deep-copy a canonical bundle, preserving bundle-level metadata."""

    copied = DataBundle()
    for key, basedata in bundle.items():
        copied[key] = basedata.copy()
    return _copy_bundle_metadata(bundle, copied)


def _bundle_units(bundle: Mapping[str, BaseData]) -> tuple[Any, Any]:
    if "Q" in bundle:
        q_units = bundle["Q"].units
    elif "Qx" in bundle:
        q_units = bundle["Qx"].units
    else:
        raise KeyError("Bundle must contain 'Q' for 1D data or 'Qx'/'Qy' for 2D data.")
    return q_units, bundle["signal"].units


def _canonical_1d_frame(frame: pandas.DataFrame) -> pandas.DataFrame:
    columns = ["Q", "I", "ISigma"]
    for column in ("QSigma", "mask"):
        if column in frame.columns:
            columns.append(column)
    return frame.loc[:, columns].copy()


def _frame_for_1d_stage(
    bundle: Mapping[str, BaseData], source_frame: pandas.DataFrame | None = None
) -> pandas.DataFrame:
    if source_frame is None:
        return frame_from_bundle(bundle)
    return source_frame.copy()


def _prepared_1d_stage(reference_bundle: Mapping[str, BaseData], frame: pandas.DataFrame) -> Prepared1DStage:
    q_units, intensity_units = _bundle_units(reference_bundle)
    bundle = bundle_from_1d_dataframe(
        _canonical_1d_frame(frame),
        q_units=q_units,
        intensity_units=intensity_units,
    )
    _copy_bundle_metadata(reference_bundle, bundle)
    return Prepared1DStage(bundle=bundle, frame=frame.copy())


def _propagated_mean_sigma(sigmas: pandas.Series) -> float:
    sigma_values = sigmas.to_numpy(dtype=float)
    return float(np.sqrt(np.square(sigma_values).sum()) / len(sigma_values))


def _sample_sem(values: pandas.Series) -> float:
    if len(values) <= 1:
        return np.nan
    return float(values.sem(ddof=1, skipna=True))


def _bounded_sigma(*, propagated_sigma: float, sem_sigma: float, value: float, relative_floor: float) -> float:
    floor_sigma = abs(float(value)) * relative_floor
    candidates = [propagated_sigma, floor_sigma]
    if np.isfinite(sem_sigma):
        candidates.append(sem_sigma)
    return float(np.max(candidates))


def _validated_range(name: str, values: RangeLike) -> tuple[float, float]:
    if len(values) != 2:
        raise ValueError(f"{name} must contain exactly two values.")
    try:
        lower = float(values[0])
        upper = float(values[1])
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must contain numeric lower and upper bounds.") from exc
    if np.isnan(lower) or np.isnan(upper):
        raise ValueError(f"{name} cannot contain NaN bounds.")
    if lower > upper:
        raise ValueError(f"{name} lower bound must be <= upper bound.")
    return lower, upper


def _validated_range_list(name: str, ranges: RangeListLike) -> list[tuple[float, float]]:
    if ranges is None:
        return []
    if not isinstance(ranges, Sequence):
        raise TypeError(f"{name} must be a sequence of [lower, upper] pairs.")
    return [_validated_range(f"{name}[{index}]", value_range) for index, value_range in enumerate(ranges)]


def _validated_relative_floor(name: str, value: float) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a numeric value.") from exc
    if np.isnan(normalized) or normalized < 0:
        raise ValueError(f"{name} must be non-negative.")
    return normalized


def _validated_nbins(nbins: int) -> int:
    if nbins < 0:
        raise ValueError("nbins must be zero or positive.")
    return int(nbins)


def copy_1d_stage(bundle: Mapping[str, BaseData], *, source_frame: pandas.DataFrame | None = None) -> Prepared1DStage:
    """Copy a canonical 1D stage and its compatibility dataframe view."""

    return Prepared1DStage(
        bundle=copy_bundle(bundle),
        frame=_frame_for_1d_stage(bundle, source_frame=source_frame),
    )


def clip_1d_bundle(
    bundle: Mapping[str, BaseData],
    *,
    data_range: Sequence[float],
    source_frame: pandas.DataFrame | None = None,
) -> Prepared1DStage:
    """Clip a canonical 1D bundle to the requested Q range."""

    lower, upper = _validated_range("data_range", data_range)
    frame = _frame_for_1d_stage(bundle, source_frame=source_frame)
    clipped = frame.query(f"{lower} <= Q < {upper}").dropna().copy()
    if len(clipped) == 0:
        raise ValueError("Data clipping range too small, no datapoints found.")
    return _prepared_1d_stage(bundle, clipped)


def omit_1d_bundle(
    bundle: Mapping[str, BaseData],
    *,
    omit_q_ranges: Sequence[Sequence[float]] | None,
    source_frame: pandas.DataFrame | None = None,
) -> Prepared1DStage:
    """Drop configured Q intervals from a canonical 1D bundle."""

    if omit_q_ranges is None:
        return copy_1d_stage(bundle, source_frame=source_frame)

    frame = _frame_for_1d_stage(bundle, source_frame=source_frame)
    for q_min, q_max in _validated_range_list("omit_q_ranges", omit_q_ranges):
        frame.drop(frame.query(f"{q_min} <= Q < {q_max}").index, inplace=True)
    return _prepared_1d_stage(bundle, frame)


def rebin_1d_bundle(
    bundle: Mapping[str, BaseData],
    *,
    nbins: int,
    iemin: float,
    qemin: float = 0.01,
    source_frame: pandas.DataFrame | None = None,
) -> Prepared1DStage:
    """Logarithmically rebin a canonical 1D bundle with uncertainty floors."""

    nbins = _validated_nbins(nbins)
    iemin = _validated_relative_floor("iemin", iemin)
    qemin = _validated_relative_floor("qemin", qemin)
    if nbins <= 0:
        raise ValueError("nbins must be positive for 1D rebinning.")

    clipped_data = _frame_for_1d_stage(bundle, source_frame=source_frame)
    q_min = clipped_data.Q.dropna().min()
    q_max = clipped_data.Q.dropna().max()
    if q_min <= 0:
        raise ValueError("Logarithmic 1D rebinning requires strictly positive Q values.")

    if np.isclose(q_min, q_max):
        rebinnable = clipped_data.loc[:, ["Q", "I", "ISigma"]].copy()
        rebinnable["_bin"] = 0
    else:
        bin_edges = np.logspace(np.log10(q_min), np.log10(q_max), num=nbins + 1)
        bin_edges[-1] = bin_edges[-1] + 1e-3 * (bin_edges[-1] - bin_edges[-2])
        bin_numbers = np.searchsorted(bin_edges, clipped_data["Q"].to_numpy(dtype=float), side="right") - 1
        valid = (bin_numbers >= 0) & (bin_numbers < nbins)
        if not np.any(valid):
            raise ValueError("1D rebinning produced no populated bins.")
        rebinnable = clipped_data.loc[valid, ["Q", "I", "ISigma"]].copy()
        rebinnable["_bin"] = bin_numbers[valid]
    if "QSigma" in clipped_data.columns:
        rebinnable["QSigma"] = clipped_data.loc[valid, "QSigma"].to_numpy(dtype=float)

    rows: list[dict[str, float]] = []
    for _bin_number, df_range in rebinnable.groupby("_bin", sort=True):
        mean_q = float(df_range["Q"].mean(skipna=True))
        mean_i = float(df_range["I"].mean(skipna=True))

        q_error = mean_q * qemin
        if "QSigma" in df_range.columns:
            q_error = _propagated_mean_sigma(df_range["QSigma"])

        rows.append(
            {
                "Q": mean_q,
                "I": mean_i,
                "ISigma": _bounded_sigma(
                    propagated_sigma=_propagated_mean_sigma(df_range["ISigma"]),
                    sem_sigma=_sample_sem(df_range["I"]),
                    value=mean_i,
                    relative_floor=iemin,
                ),
                "QSigma": _bounded_sigma(
                    propagated_sigma=q_error,
                    sem_sigma=_sample_sem(df_range["Q"]),
                    value=mean_q,
                    relative_floor=qemin,
                ),
            }
        )

    return _prepared_1d_stage(bundle, pandas.DataFrame(rows, columns=["Q", "I", "ISigma", "QSigma"]))


def prepare_1d_bundle(
    raw_bundle: Mapping[str, BaseData],
    *,
    data_range: Sequence[float],
    omit_q_ranges: Sequence[Sequence[float]] | None = None,
    nbins: int = 0,
    iemin: float = 0.01,
    qemin: float = 0.01,
    source_frame: pandas.DataFrame | None = None,
) -> Prepared1DResult:
    """Run the full 1D preprocessing chain on a canonical raw bundle."""

    _validated_range("data_range", data_range)
    _validated_range_list("omit_q_ranges", omit_q_ranges)
    nbins = _validated_nbins(nbins)
    iemin = _validated_relative_floor("iemin", iemin)
    qemin = _validated_relative_floor("qemin", qemin)
    clipped = clip_1d_bundle(raw_bundle, data_range=data_range, source_frame=source_frame)
    clipped = omit_1d_bundle(clipped.bundle, omit_q_ranges=omit_q_ranges, source_frame=clipped.frame)
    if nbins != 0:
        binned = rebin_1d_bundle(clipped.bundle, nbins=nbins, iemin=iemin, qemin=qemin, source_frame=clipped.frame)
    else:
        binned = copy_1d_stage(clipped.bundle, source_frame=clipped.frame)
    return Prepared1DResult(clipped=clipped, binned=binned)


def _stage_for_2d_bundle(
    bundle: Mapping[str, BaseData], source_stage: Mapping[str, Any] | None = None
) -> dict[str, np.ndarray]:
    if source_stage is None:
        return raw_2d_stage_from_bundle(bundle)
    return {key: np.array(value, copy=True) for key, value in source_stage.items()}


def clip_2d_bundle(
    bundle: Mapping[str, BaseData],
    *,
    data_range: Sequence[float],
    ortho_q0_range: Sequence[float],
    ortho_q1_range: Sequence[float],
    source_stage: Mapping[str, Any] | None = None,
) -> DataBundle:
    """Crop a canonical 2D bundle to the requested radial and orthogonal Q limits."""

    data_range = _validated_range("data_range", data_range)
    ortho_q0_range = _validated_range("ortho_q0_range", ortho_q0_range)
    ortho_q1_range = _validated_range("ortho_q1_range", ortho_q1_range)
    raw_stage = _stage_for_2d_bundle(bundle, source_stage=source_stage)
    intensity = raw_stage["I"]
    intensity_sigma = raw_stage["ISigma"]
    q1 = raw_stage["Qx"]
    q0 = raw_stage["Qy"]
    mask = raw_stage.get("mask", np.zeros(intensity.shape, dtype=bool)).astype(bool)

    within_limits = (
        (np.abs(q1) > ortho_q1_range[0])
        & (np.abs(q1) < ortho_q1_range[1])
        & (np.abs(q0) > ortho_q0_range[0])
        & (np.abs(q0) < ortho_q0_range[1])
        & (np.sqrt(q1**2 + q0**2) > data_range[0])
        & (np.sqrt(q1**2 + q0**2) < data_range[1])
    ).astype(bool) & np.invert(mask)

    q0_hits = np.argwhere(within_limits.sum(axis=1) > 0).flatten()
    q1_hits = np.argwhere(within_limits.sum(axis=0) > 0).flatten()
    if len(q0_hits) == 0:
        raise ValueError("Could not determine valid crop limits for axis 0 (y).")
    if len(q1_hits) == 0:
        raise ValueError("Could not determine valid crop limits for axis 1 (x).")

    q0_limits = (q0_hits.min(), q0_hits.max() + 1)
    q1_limits = (q1_hits.min(), q1_hits.max() + 1)
    q_units, intensity_units = _bundle_units(bundle)
    clipped = bundle_from_2d_arrays(
        intensity=intensity[q0_limits[0] : q0_limits[1], q1_limits[0] : q1_limits[1]],
        intensity_sigma=intensity_sigma[q0_limits[0] : q0_limits[1], q1_limits[0] : q1_limits[1]],
        qx=q1[q0_limits[0] : q0_limits[1], q1_limits[0] : q1_limits[1]],
        qy=q0[q0_limits[0] : q0_limits[1], q1_limits[0] : q1_limits[1]],
        mask=mask[q0_limits[0] : q0_limits[1], q1_limits[0] : q1_limits[1]],
        q_units=q_units,
        intensity_units=intensity_units,
    )
    return _copy_bundle_metadata(bundle, clipped)


def omit_2d_bundle(
    bundle: Mapping[str, BaseData], *, omit_q_ranges: Sequence[Sequence[float]] | None = None
) -> DataBundle:
    """Return the 2D bundle unchanged while omission remains unsupported."""

    if omit_q_ranges is not None:
        logger.warning("2D omit ranges are not implemented; returning the clipped bundle unchanged.")
    return copy_bundle(bundle)


def rebin_2d_bundle(
    bundle: Mapping[str, BaseData], *, nbins: int, iemin: float = 0.01, qemin: float = 0.01
) -> DataBundle:
    """Return the 2D bundle unchanged while rebinning remains unsupported."""

    nbins = _validated_nbins(nbins)
    iemin = _validated_relative_floor("iemin", iemin)
    qemin = _validated_relative_floor("qemin", qemin)
    logger.warning(
        "2D rebinning is not implemented yet; returning the clipped bundle unchanged (nbins=%s, iemin=%s, qemin=%s).",
        nbins,
        iemin,
        qemin,
    )
    return copy_bundle(bundle)


def reconstruct_2d_from_clipped_bundle(bundle: Mapping[str, BaseData], model_i_1d: np.ndarray) -> np.ndarray:
    """Map flattened model intensities back into the clipped 2D image geometry."""

    if bundle_dimension(bundle) != 2:
        raise ValueError("reconstruct_2d_from_clipped_bundle requires a canonical 2D scattering bundle.")

    intensity = np.asarray(bundle["signal"].signal, dtype=float)
    intensity_sigma = _combine_uncertainties(bundle["signal"])
    mask = np.zeros_like(intensity, dtype=bool)
    if "mask" in bundle:
        mask = np.asarray(bundle["mask"].signal, dtype=bool)

    valid = np.isfinite(intensity) & np.isfinite(intensity_sigma) & (intensity_sigma != 0) & np.invert(mask)
    model_i_1d = np.asarray(model_i_1d, dtype=float).reshape(-1)
    if valid.sum() != model_i_1d.size:
        raise ValueError("Model intensity length does not match the number of valid pixels in the clipped 2D bundle.")

    reconstructed = np.full(intensity.shape, np.nan)
    reconstructed[valid] = model_i_1d
    return reconstructed


def prepare_2d_bundle(
    raw_bundle: Mapping[str, BaseData],
    *,
    data_range: Sequence[float],
    ortho_q0_range: Sequence[float],
    ortho_q1_range: Sequence[float],
    omit_q_ranges: Sequence[Sequence[float]] | None = None,
    nbins: int = 0,
    iemin: float = 0.01,
    qemin: float = 0.01,
    source_stage: Mapping[str, Any] | None = None,
) -> Prepared2DResult:
    """Run the current 2D preprocessing chain on a canonical raw bundle."""

    _validated_range("data_range", data_range)
    _validated_range("ortho_q0_range", ortho_q0_range)
    _validated_range("ortho_q1_range", ortho_q1_range)
    _validated_range_list("omit_q_ranges", omit_q_ranges)
    nbins = _validated_nbins(nbins)
    iemin = _validated_relative_floor("iemin", iemin)
    qemin = _validated_relative_floor("qemin", qemin)
    clipped = clip_2d_bundle(
        raw_bundle,
        data_range=data_range,
        ortho_q0_range=ortho_q0_range,
        ortho_q1_range=ortho_q1_range,
        source_stage=source_stage,
    )
    clipped = omit_2d_bundle(clipped, omit_q_ranges=omit_q_ranges)
    if nbins != 0:
        binned = rebin_2d_bundle(clipped, nbins=nbins, iemin=iemin, qemin=qemin)
    else:
        binned = copy_bundle(clipped)
    return Prepared2DResult(clipped=clipped, binned=binned)


__all__ = [
    "Prepared1DResult",
    "Prepared1DStage",
    "Prepared2DResult",
    "clip_1d_bundle",
    "clip_2d_bundle",
    "copy_bundle",
    "copy_1d_stage",
    "omit_1d_bundle",
    "omit_2d_bundle",
    "prepare_1d_bundle",
    "prepare_2d_bundle",
    "rebin_1d_bundle",
    "rebin_2d_bundle",
    "reconstruct_2d_from_clipped_bundle",
]
