from __future__ import annotations

from modacor import ureg
from modacor.dataclasses.basedata import BaseData
from modacor.dataclasses.databundle import DataBundle
from modacor.dataclasses.processing_data import ProcessingData

MODACOR_IMPORT_MODE = "installed"
MODACOR_SOURCE = None

__all__ = [
    "BaseData",
    "DataBundle",
    "MODACOR_IMPORT_MODE",
    "MODACOR_SOURCE",
    "ProcessingData",
    "ureg",
]
