"""Public McSAS3 API centered on canonical ProcessingData workflows."""

from .data_adapters import (
    DEFAULT_ANALYSIS_STAGE,
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    analysis_data_from_bundle,
    selected_bundle_from_processing,
)
from .data_model import BaseData, DataBundle, ProcessingData
from .workflows import (
    load_result_processing_data,
    optimize_processing_data,
    prepare_1d_processing_data,
    prepare_1d_processing_data_from_file,
    prepare_2d_processing_data,
    prepare_2d_processing_data_from_file,
    store_result_processing_data,
)

__version__ = "1.0.6"

__all__ = [
    "BaseData",
    "DEFAULT_ANALYSIS_STAGE",
    "DataBundle",
    "ProcessingData",
    "STAGE_BINNED",
    "STAGE_CLIPPED",
    "STAGE_RAW",
    "analysis_data_from_bundle",
    "load_result_processing_data",
    "optimize_processing_data",
    "prepare_1d_processing_data",
    "prepare_1d_processing_data_from_file",
    "prepare_2d_processing_data",
    "prepare_2d_processing_data_from_file",
    "selected_bundle_from_processing",
    "store_result_processing_data",
]
