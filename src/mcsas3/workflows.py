from pathlib import Path
from typing import Any

import pandas

from .data_adapters import (
    DEFAULT_ANALYSIS_STAGE,
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    bundle_from_1d_dataframe,
    bundle_from_2d_stage,
    selected_bundle_from_processing,
    set_processing_analysis_stage,
)
from .data_model import BaseData, DataBundle, ProcessingData
from .ingestion import load_1d_dataframe_from_file, load_2d_stage_from_file
from .mc_hat import McHat
from .mc_hdf import PROCESSING_DATA_GROUP, ResultIndex, loadProcessingData, storeKVPairs, storeProcessingData
from .preprocessing import copy_bundle, prepare_1d_bundle, prepare_2d_bundle


def _empty_processing() -> ProcessingData:
    return ProcessingData()


def _result_mcdata_path(result_index: int) -> Path:
    return ResultIndex(result_index).nxsEntryPoint / "mcdata"


def _normalized_1d_file_workflow_config(read_config: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "QUnits": "sourceQUnits",
        "IUnits": "sourceIntensityUnits",
        "Q_units": "sourceQUnits",
        "I_units": "sourceIntensityUnits",
        "QEMin": "qemin",
    }
    defaults = {
        "loader": None,
        "csvargs": None,
        "pathDict": None,
        "dataRange": [-float("inf"), float("inf")],
        "omitQRanges": None,
        "nbins": 100,
        "IEmin": 0.01,
        "qemin": 0.01,
        "analysisStage": DEFAULT_ANALYSIS_STAGE,
        "sourceQUnits": None,
        "sourceIntensityUnits": None,
    }
    normalized = defaults.copy()

    for key, value in read_config.items():
        normalized_key = aliases.get(key, key)
        if normalized_key not in normalized:
            raise ValueError(f"Unsupported 1D workflow configuration key '{key}'.")

        if normalized[normalized_key] != defaults[normalized_key] and normalized[normalized_key] != value:
            raise ValueError(
                f"Conflicting configuration values provided for '{normalized_key}': "
                f"{normalized[normalized_key]!r} and {value!r}."
            )
        normalized[normalized_key] = value

    return normalized


def _normalized_2d_file_workflow_config(read_config: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "QUnits": "sourceQUnits",
        "IUnits": "sourceIntensityUnits",
        "Q_units": "sourceQUnits",
        "I_units": "sourceIntensityUnits",
        "QEMin": "qemin",
    }
    defaults = {
        "loader": None,
        "pathDict": None,
        "dataRange": [0, float("inf")],
        "orthoQ0Range": [0, float("inf")],
        "orthoQ1Range": [0, float("inf")],
        "omitQRanges": None,
        "nbins": 100,
        "IEmin": 0.01,
        "qemin": 0.01,
        "analysisStage": DEFAULT_ANALYSIS_STAGE,
        "sourceQUnits": None,
        "sourceIntensityUnits": None,
    }
    normalized = defaults.copy()

    for key, value in read_config.items():
        normalized_key = aliases.get(key, key)
        if normalized_key not in normalized:
            raise ValueError(f"Unsupported 2D workflow configuration key '{key}'.")

        if normalized[normalized_key] != defaults[normalized_key] and normalized[normalized_key] != value:
            raise ValueError(
                f"Conflicting configuration values provided for '{normalized_key}': "
                f"{normalized[normalized_key]!r} and {value!r}."
            )
        normalized[normalized_key] = value

    return normalized


def prepare_1d_processing_data(
    raw_data: pandas.DataFrame | DataBundle | dict[str, BaseData],
    *,
    data_range=None,
    omit_q_ranges=None,
    nbins: int = 0,
    iemin: float = 0.01,
    qemin: float = 0.01,
    analysis_stage: str = DEFAULT_ANALYSIS_STAGE,
    source_q_units=None,
    source_intensity_units=None,
) -> ProcessingData:
    """Build canonical 1D ProcessingData directly from a raw table or bundle."""

    if data_range is None:
        data_range = [-float("inf"), float("inf")]

    source_frame = None
    if isinstance(raw_data, pandas.DataFrame):
        raw_bundle = bundle_from_1d_dataframe(
            raw_data,
            source_q_units=source_q_units,
            source_intensity_units=source_intensity_units,
        )
        source_frame = raw_data
    elif isinstance(raw_data, dict):
        raw_bundle = copy_bundle(raw_data)
    else:
        raw_bundle = copy_bundle(raw_data)

    prepared = prepare_1d_bundle(
        raw_bundle,
        data_range=data_range,
        omit_q_ranges=omit_q_ranges,
        nbins=nbins,
        iemin=iemin,
        qemin=qemin,
        source_frame=source_frame,
    )
    processing = _empty_processing()
    processing[STAGE_RAW] = copy_bundle(raw_bundle)
    processing[STAGE_CLIPPED] = prepared.clipped.bundle
    processing[STAGE_BINNED] = prepared.binned.bundle
    set_processing_analysis_stage(processing, analysis_stage)
    return processing


def prepare_2d_processing_data(
    raw_bundle: DataBundle | dict[str, BaseData],
    *,
    data_range,
    ortho_q0_range,
    ortho_q1_range,
    omit_q_ranges=None,
    nbins: int = 0,
    iemin: float = 0.01,
    qemin: float = 0.01,
    analysis_stage: str = DEFAULT_ANALYSIS_STAGE,
) -> ProcessingData:
    """Build canonical 2D ProcessingData directly from a raw 2D bundle."""

    canonical_raw = copy_bundle(raw_bundle)
    prepared = prepare_2d_bundle(
        canonical_raw,
        data_range=data_range,
        ortho_q0_range=ortho_q0_range,
        ortho_q1_range=ortho_q1_range,
        omit_q_ranges=omit_q_ranges,
        nbins=nbins,
        iemin=iemin,
        qemin=qemin,
    )
    processing = _empty_processing()
    processing[STAGE_RAW] = canonical_raw
    processing[STAGE_CLIPPED] = prepared.clipped
    processing[STAGE_BINNED] = prepared.binned
    set_processing_analysis_stage(processing, analysis_stage)
    return processing


def prepare_2d_processing_data_from_file(
    filename: Path,
    *,
    result_index: int = 1,
    **read_config: Any,
) -> ProcessingData:
    """File-ingest helper returning canonical 2D ProcessingData without constructing McData2D."""

    _ = result_index
    config = _normalized_2d_file_workflow_config(read_config)
    loaded = load_2d_stage_from_file(
        filename,
        loader=config["loader"],
        path_dict=config["pathDict"],
    )
    source_q_units = config["sourceQUnits"] if config["sourceQUnits"] is not None else loaded.source_q_units
    source_intensity_units = (
        config["sourceIntensityUnits"] if config["sourceIntensityUnits"] is not None else loaded.source_intensity_units
    )
    raw_bundle = bundle_from_2d_stage(
        loaded.stage,
        source_q_units=source_q_units,
        source_intensity_units=source_intensity_units,
    )
    return prepare_2d_processing_data(
        raw_bundle,
        data_range=config["dataRange"],
        ortho_q0_range=config["orthoQ0Range"],
        ortho_q1_range=config["orthoQ1Range"],
        omit_q_ranges=config["omitQRanges"],
        nbins=config["nbins"],
        iemin=config["IEmin"],
        qemin=config["qemin"],
        analysis_stage=config["analysisStage"],
    )


def prepare_1d_processing_data_from_file(
    filename: Path,
    *,
    result_index: int = 1,
    **read_config: Any,
) -> ProcessingData:
    """File-ingest helper returning canonical 1D ProcessingData without constructing McData1D."""

    config = _normalized_1d_file_workflow_config(read_config)
    loaded = load_1d_dataframe_from_file(
        filename,
        loader=config["loader"],
        csvargs=config["csvargs"],
        path_dict=config["pathDict"],
    )
    source_q_units = config["sourceQUnits"] if config["sourceQUnits"] is not None else loaded.source_q_units
    source_intensity_units = (
        config["sourceIntensityUnits"] if config["sourceIntensityUnits"] is not None else loaded.source_intensity_units
    )
    return prepare_1d_processing_data(
        loaded.frame,
        data_range=config["dataRange"],
        omit_q_ranges=config["omitQRanges"],
        nbins=config["nbins"],
        iemin=config["IEmin"],
        qemin=config["qemin"],
        analysis_stage=config["analysisStage"],
        source_q_units=source_q_units,
        source_intensity_units=source_intensity_units,
    )


def load_result_processing_data(filename: Path, *, result_index: int = 1) -> ProcessingData:
    """Load canonical ProcessingData from an McSAS3 result file."""

    path = _result_mcdata_path(result_index)
    processing = loadProcessingData(filename, path / PROCESSING_DATA_GROUP, default=None)
    if processing is None:
        raise ValueError(
            f"Result file {filename} does not contain canonical processing data at {path / PROCESSING_DATA_GROUP}."
        )
    return processing


def store_result_processing_data(
    filename: Path,
    processing: ProcessingData,
    *,
    result_index: int = 1,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store canonical ProcessingData and optional metadata into an McSAS3 result file."""

    path = _result_mcdata_path(result_index)
    storeProcessingData(filename=filename, path=path / PROCESSING_DATA_GROUP, processing=processing)
    if metadata:
        storeKVPairs(filename, path, metadata.items())


def optimize_processing_data(
    processing: ProcessingData,
    result_file: Path,
    *,
    result_index: int = 1,
    store_processing: bool = True,
    processing_metadata: dict[str, Any] | None = None,
    hat: McHat | None = None,
    **hat_kwargs: Any,
) -> McHat:
    """Run McSAS optimization from canonical ProcessingData."""

    if hat is not None and hat_kwargs:
        raise ValueError("Provide either an McHat instance or McHat keyword arguments, not both.")

    if store_processing:
        store_result_processing_data(
            result_file,
            processing,
            result_index=result_index,
            metadata=processing_metadata,
        )

    active_hat = hat if hat is not None else McHat(resultIndex=result_index, **hat_kwargs)
    active_hat.run(selected_bundle_from_processing(processing), result_file, resultIndex=result_index)
    return active_hat


__all__ = [
    "load_result_processing_data",
    "optimize_processing_data",
    "prepare_1d_processing_data",
    "prepare_1d_processing_data_from_file",
    "prepare_2d_processing_data",
    "prepare_2d_processing_data_from_file",
    "store_result_processing_data",
]
