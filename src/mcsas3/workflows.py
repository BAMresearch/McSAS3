from pathlib import Path
from typing import Any

import pandas

from .data_adapters import (
    DEFAULT_ANALYSIS_STAGE,
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    bundle_from_1d_dataframe,
    selected_bundle_from_processing,
    set_processing_analysis_stage,
)
from .data_model import BaseData, DataBundle, ProcessingData
from .mc_data_1d import McData1D
from .mc_hat import McHat
from .mc_hdf import PROCESSING_DATA_GROUP, ResultIndex, loadProcessingData, storeKVPairs, storeProcessingData
from .preprocessing import copy_bundle, prepare_1d_bundle, prepare_2d_bundle


def _empty_processing() -> ProcessingData:
    return ProcessingData()


def _result_mcdata_path(result_index: int) -> Path:
    return ResultIndex(result_index).nxsEntryPoint / "mcdata"


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


def prepare_1d_processing_data_from_file(
    filename: Path,
    *,
    result_index: int = 1,
    **read_config: Any,
) -> ProcessingData:
    """Transitional file-ingest helper returning canonical 1D ProcessingData."""

    transitional = McData1D(filename=filename, resultIndex=result_index, **read_config)
    processing = transitional.to_processing_data()
    set_processing_analysis_stage(processing, transitional.analysisStage)
    return processing


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
    "store_result_processing_data",
]
