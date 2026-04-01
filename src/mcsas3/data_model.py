from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _workspace_modacor_src() -> Path:
    configured = os.environ.get("MCSAS3_MODACOR_SRC")
    if configured:
        return Path(configured).expanduser().resolve()

    repo_root = Path(__file__).resolve().parents[2]
    return repo_root.parent / "MoDaCor" / "src"


def _import_modacor() -> dict[str, Any]:
    try:
        from modacor import ureg as imported_ureg
        from modacor.dataclasses.basedata import BaseData as imported_basedata
        from modacor.dataclasses.databundle import DataBundle as imported_databundle
        from modacor.dataclasses.processing_data import ProcessingData as imported_processing_data

        return {
            "BaseData": imported_basedata,
            "DataBundle": imported_databundle,
            "ProcessingData": imported_processing_data,
            "ureg": imported_ureg,
            "mode": "installed",
            "source": None,
        }
    except ImportError as first_error:
        workspace_src = _workspace_modacor_src()
        workspace_src_str = str(workspace_src)
        if workspace_src.is_dir() and workspace_src_str not in sys.path:
            sys.path.insert(0, workspace_src_str)

        try:
            from modacor import ureg as imported_ureg
            from modacor.dataclasses.basedata import BaseData as imported_basedata
            from modacor.dataclasses.databundle import DataBundle as imported_databundle
            from modacor.dataclasses.processing_data import ProcessingData as imported_processing_data
        except ImportError as workspace_error:
            raise ImportError(
                "McSAS3 could not import MoDaCor data classes. Install the 'modacor' package or "
                f"place the sibling checkout at '{workspace_src}'."
            ) from workspace_error

        return {
            "BaseData": imported_basedata,
            "DataBundle": imported_databundle,
            "ProcessingData": imported_processing_data,
            "ureg": imported_ureg,
            "mode": "workspace",
            "source": workspace_src,
            "initial_error": first_error,
        }


_MODACOR_EXPORTS = _import_modacor()

BaseData = _MODACOR_EXPORTS["BaseData"]
DataBundle = _MODACOR_EXPORTS["DataBundle"]
ProcessingData = _MODACOR_EXPORTS["ProcessingData"]
ureg = _MODACOR_EXPORTS["ureg"]
MODACOR_IMPORT_MODE = _MODACOR_EXPORTS["mode"]
MODACOR_SOURCE = _MODACOR_EXPORTS["source"]

__all__ = [
    "BaseData",
    "DataBundle",
    "MODACOR_IMPORT_MODE",
    "MODACOR_SOURCE",
    "ProcessingData",
    "ureg",
]
