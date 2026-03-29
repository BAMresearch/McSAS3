from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import attrs
import h5py
import numpy as np
import pandas

DEFAULT_1D_CSVARGS = {
    "sep": r"\s+",
    "header": None,
    "names": ["Q", "I", "ISigma"],
}


@attrs.frozen
class Loaded1DData:
    """Raw 1D table plus the metadata detected during ingestion."""

    frame: pandas.DataFrame = attrs.field(validator=attrs.validators.instance_of(pandas.DataFrame))
    loader: str = attrs.field(validator=attrs.validators.instance_of(str))
    source_q_units: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    source_intensity_units: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )


@attrs.frozen
class Loaded2DData:
    """Raw 2D stage plus the metadata detected during ingestion."""

    stage: dict[str, np.ndarray] = attrs.field(validator=attrs.validators.instance_of(dict))
    frame: pandas.DataFrame = attrs.field(validator=attrs.validators.instance_of(pandas.DataFrame))
    loader: str = attrs.field(validator=attrs.validators.instance_of(str))
    source_q_units: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    source_intensity_units: str | None = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )


def _obj_bytes_to_str(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.ndarray):
        return value.astype("str")
    return value


def _dataset_units(h5f: h5py.File, dataset_path: str) -> str | None:
    if dataset_path not in h5f:
        return None
    dataset = h5f[dataset_path]
    for attr_name in ("units", "unit"):
        if attr_name in dataset.attrs:
            return str(_obj_bytes_to_str(dataset.attrs[attr_name]))
    return None


def _detected_q_units_from_path_dict(h5f: h5py.File, path_dict: Mapping[str, str]) -> str | None:
    if "Q" in path_dict:
        return _dataset_units(h5f, str(path_dict["Q"]))
    if "Qx" in path_dict and "Qy" in path_dict:
        qx_units = _dataset_units(h5f, str(path_dict["Qx"]))
        qy_units = _dataset_units(h5f, str(path_dict["Qy"]))
        if qx_units is not None and qy_units is not None and qx_units != qy_units:
            raise ValueError("pathDict provides inconsistent Q units for 'Qx' and 'Qy' datasets.")
        return qx_units if qx_units is not None else qy_units
    return None


def _validated_1d_frame(frame: pandas.DataFrame) -> pandas.DataFrame:
    required_columns = {"Q", "I", "ISigma"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise KeyError(f"1D input data is missing required columns: {sorted(missing_columns)}")

    validated = frame.copy()
    for column in ("Q", "I", "ISigma"):
        validated[column] = pandas.to_numeric(validated[column], errors="raise").astype(float)
    if "QSigma" in validated.columns:
        validated["QSigma"] = pandas.to_numeric(validated["QSigma"], errors="raise").astype(float)
    if "mask" in validated.columns:
        validated["mask"] = validated["mask"].astype(bool)
    return validated


def _load_nexus_raw_data(
    filename: Path,
    *,
    path_dict: Mapping[str, str] | None = None,
) -> tuple[dict[str, np.ndarray], str | None, str | None]:
    raw_data: dict[str, np.ndarray] = {}
    detected_q_units = None
    detected_intensity_units = None

    with h5py.File(filename, "r") as h5f:
        if path_dict is not None:
            required_signal_keys = {"I", "ISigma"}
            has_combined_q = "Q" in path_dict
            has_split_q = {"Qx", "Qy"}.issubset(path_dict.keys())
            if not isinstance(path_dict, Mapping) or not required_signal_keys.issubset(path_dict.keys()):
                raise ValueError("pathDict must provide 'I' and 'ISigma' dataset paths.")
            if not has_combined_q and not has_split_q:
                raise ValueError("pathDict must provide either 'Q' or both 'Qx' and 'Qy' dataset paths.")
            for key, dataset_path in path_dict.items():
                raw_data[key] = h5f[str(dataset_path)][()].squeeze()
            detected_q_units = _detected_q_units_from_path_dict(h5f, path_dict)
            detected_intensity_units = _dataset_units(h5f, str(path_dict["I"]))
        else:
            signal_path = "/"
            while "default" in h5f[signal_path].attrs:
                signal_path_add = _obj_bytes_to_str(h5f[signal_path].attrs["default"])
                signal_path += f"{signal_path_add}/"

            if "signal" not in h5f[signal_path].attrs:
                raise ValueError("No signal dataset found at the default NeXus path.")

            signal_label = _obj_bytes_to_str(h5f[signal_path].attrs["signal"])
            signal_dataset_path = f"{signal_path}{signal_label}"
            raw_data["I"] = h5f[signal_dataset_path][()].squeeze()
            detected_intensity_units = _dataset_units(h5f, signal_dataset_path)

            if f"{signal_label}_uncertainty" in h5f[signal_path].attrs:
                uncertainty_label = _obj_bytes_to_str(h5f[signal_path].attrs[f"{signal_label}_uncertainty"])
                raw_data["ISigma"] = h5f[f"{signal_path}{uncertainty_label}"][()].squeeze()
            elif "uncertainties" in h5f[signal_dataset_path].attrs:
                uncertainty_label = _obj_bytes_to_str(h5f[signal_dataset_path].attrs["uncertainties"])
                raw_data["ISigma"] = h5f[f"{signal_path}{uncertainty_label}"][()].squeeze()
            else:
                raw_data["ISigma"] = raw_data["I"] * 0.001

            if "mask" in h5f[signal_path].attrs:
                mask_label = _obj_bytes_to_str(h5f[signal_path].attrs["mask"])
                raw_data["mask"] = h5f[f"{signal_path}{mask_label}"][()].squeeze()

            axes_label = None
            if "axes" in h5f[signal_path].attrs:
                axes_label = "axes"
            elif "I_axes" in h5f[signal_path].attrs:
                axes_label = "I_axes"
            if axes_label is None:
                raise ValueError("Could not find the axes label associated with the NeXus signal dataset.")

            axes_object = _obj_bytes_to_str(h5f[signal_path].attrs[axes_label])
            q_label = next((candidate for candidate in ("q", "Q") if candidate in axes_object), None)
            if q_label is None:
                raise ValueError("Could not find a Q axis associated with the NeXus signal dataset.")
            raw_data["Q"] = h5f[f"{signal_path}{q_label}"][()].squeeze()
            detected_q_units = _dataset_units(h5f, f"{signal_path}{q_label}")

    return raw_data, detected_q_units, detected_intensity_units


def _load_1d_csv(filename: Path, *, csvargs: Mapping[str, Any] | None = None) -> Loaded1DData:
    local_csvargs = dict(DEFAULT_1D_CSVARGS)
    if csvargs is not None:
        local_csvargs.update(dict(csvargs))
    frame = pandas.read_csv(filename, **local_csvargs)
    return Loaded1DData(frame=_validated_1d_frame(frame), loader="from_csv")


def _load_1d_pdh(filename: Path, *, csvargs: Mapping[str, Any] | None = None) -> Loaded1DData:
    skiprows = 5
    stop_line = None
    with open(filename) as fd:
        for line_number, line in enumerate(fd):
            if line.startswith("<?xml"):
                stop_line = line_number
                break

    local_csvargs = dict(DEFAULT_1D_CSVARGS)
    if csvargs is not None:
        local_csvargs.update(dict(csvargs))
    local_csvargs["skiprows"] = skiprows
    if stop_line is not None:
        local_csvargs["nrows"] = stop_line - skiprows

    frame = pandas.read_csv(filename, **local_csvargs)
    return Loaded1DData(frame=_validated_1d_frame(frame), loader="from_pdh")


def _load_1d_nexus(filename: Path, *, path_dict: Mapping[str, str] | None = None) -> Loaded1DData:
    raw_data, detected_q_units, detected_intensity_units = _load_nexus_raw_data(filename, path_dict=path_dict)

    if np.asarray(raw_data["Q"]).ndim > 1:
        raise ValueError("1D ingestion helpers cannot read 2D NeXus data directly.")

    return Loaded1DData(
        frame=_validated_1d_frame(pandas.DataFrame(data=raw_data)),
        loader="from_nexus",
        source_q_units=None if detected_q_units is None else str(detected_q_units),
        source_intensity_units=None if detected_intensity_units is None else str(detected_intensity_units),
    )


def _loaded_2d_from_raw_data(
    raw_data: dict[str, np.ndarray],
    *,
    detected_q_units: str | None,
    detected_intensity_units: str | None,
) -> Loaded2DData:
    if "Qx" in raw_data and "Qy" in raw_data:
        qx = np.array(raw_data["Qx"], copy=True)
        qy = np.array(raw_data["Qy"], copy=True)
    else:
        if "Q" not in raw_data:
            raise ValueError("2D NeXus ingestion requires either 'Q' or explicit 'Qx'/'Qy' datasets.")
        q_data = np.asarray(raw_data["Q"])
        if q_data.ndim < 3:
            raise ValueError("2D ingestion helpers require a multidimensional Q dataset.")
        nonzero_axes = [axis_index for axis_index in range(q_data.shape[0]) if np.any(q_data[axis_index])]
        if len(nonzero_axes) < 2:
            raise ValueError("2D ingestion helpers could not resolve non-zero Qx/Qy components from the Q dataset.")
        qy = np.array(q_data[nonzero_axes[0]].squeeze(), copy=True)
        qx = np.array(q_data[nonzero_axes[1]].squeeze(), copy=True)

    intensity = np.array(raw_data["I"], copy=True)
    intensity_sigma = np.array(raw_data["ISigma"], copy=True)
    if intensity.ndim != 2 or intensity_sigma.ndim != 2 or qx.ndim != 2 or qy.ndim != 2:
        raise ValueError("2D ingestion helpers require image-shaped I, ISigma, Qx, and Qy arrays.")
    if intensity.shape != intensity_sigma.shape or intensity.shape != qx.shape or intensity.shape != qy.shape:
        raise ValueError("2D ingestion helpers require matching I, ISigma, Qx, and Qy shapes.")

    stage = {
        "Qx": qx,
        "Qy": qy,
        "I": intensity,
        "ISigma": intensity_sigma,
    }
    if "mask" in raw_data:
        stage["mask"] = np.array(raw_data["mask"], dtype=bool, copy=True)

    frame = pandas.DataFrame({key: value.flatten() for key, value in stage.items()})
    return Loaded2DData(
        stage=stage,
        frame=frame,
        loader="from_nexus",
        source_q_units=None if detected_q_units is None else str(detected_q_units),
        source_intensity_units=None if detected_intensity_units is None else str(detected_intensity_units),
    )


def load_1d_dataframe_from_file(
    filename: Path,
    *,
    loader: str | None = None,
    csvargs: Mapping[str, Any] | None = None,
    path_dict: Mapping[str, str] | None = None,
) -> Loaded1DData:
    """Load a raw 1D table plus detected metadata from a file."""

    source = Path(filename)
    if not source.is_file():
        raise FileNotFoundError(f"Input data file {source} must exist.")

    effective_loader = loader
    if effective_loader is None:
        suffix = source.suffix.lower()
        if suffix == ".pdh":
            effective_loader = "from_pdh"
        elif suffix in {".csv", ".dat", ".txt"}:
            effective_loader = "from_csv"
        elif suffix in {".h5", ".hdf5", ".nx", ".nxs"}:
            effective_loader = "from_nexus"
        else:
            raise ValueError(f"Could not determine a supported loader for input file {source}.")

    if effective_loader == "from_pdh":
        return _load_1d_pdh(source, csvargs=csvargs)
    if effective_loader == "from_csv":
        return _load_1d_csv(source, csvargs=csvargs)
    if effective_loader == "from_nexus":
        return _load_1d_nexus(source, path_dict=path_dict)
    raise ValueError(f"Unsupported 1D loader '{effective_loader}'.")


def load_2d_stage_from_file(
    filename: Path,
    *,
    loader: str | None = None,
    path_dict: Mapping[str, str] | None = None,
) -> Loaded2DData:
    """Load a raw 2D stage plus detected metadata from a file."""

    source = Path(filename)
    if not source.is_file():
        raise FileNotFoundError(f"Input data file {source} must exist.")

    effective_loader = loader
    if effective_loader is None:
        suffix = source.suffix.lower()
        if suffix in {".h5", ".hdf5", ".nx", ".nxs"}:
            effective_loader = "from_nexus"
        else:
            raise ValueError(f"Could not determine a supported 2D loader for input file {source}.")

    if effective_loader != "from_nexus":
        raise ValueError(f"Unsupported 2D loader '{effective_loader}'.")

    raw_data, detected_q_units, detected_intensity_units = _load_nexus_raw_data(source, path_dict=path_dict)
    return _loaded_2d_from_raw_data(
        raw_data,
        detected_q_units=detected_q_units,
        detected_intensity_units=detected_intensity_units,
    )


__all__ = [
    "DEFAULT_1D_CSVARGS",
    "Loaded1DData",
    "Loaded2DData",
    "load_1d_dataframe_from_file",
    "load_2d_stage_from_file",
]
