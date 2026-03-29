from pathlib import Path, PurePosixPath

import numpy as np
import pandas
import pandas.testing as pdt

from mcsas3.data_adapters import DEFAULT_INTENSITY_UNITS, STAGE_BINNED, STAGE_RAW, bundle_from_1d_dataframe
from mcsas3.data_model import ProcessingData
from mcsas3.mc_hdf import ResultIndex, loadKV, loadProcessingData, storeKV, storeKVPairs, storeProcessingData


def test_result_index_builds_expected_entry_path():
    assert ResultIndex(3).nxsEntryPoint == PurePosixPath("/analyses/MCResult3")


def test_loadkv_returns_default_for_missing_path(tmp_path):
    filename = tmp_path / "missing.h5"

    assert loadKV(filename, PurePosixPath("/does/not/exist"), default="fallback") == "fallback"


def test_storekv_round_trips_path_and_nested_dict_payloads(tmp_path):
    filename = tmp_path / "payloads.h5"
    source_path = Path("nested/datafile.dat")
    payload = {
        "labels": np.array(["alpha", "beta"]),
        "meta": {
            "count": 2,
            "scale": 1.5,
        },
    }

    storeKV(filename, PurePosixPath("/config/source"), source_path)
    storeKVPairs(filename, PurePosixPath("/payload"), payload.items())

    assert loadKV(filename, PurePosixPath("/config/source"), datatype=Path) == source_path

    loaded_payload = loadKV(filename, PurePosixPath("/payload"), datatype="dict")
    assert loaded_payload["labels"].tolist() == ["alpha", "beta"]
    assert loaded_payload["meta"] == {"count": 2, "scale": 1.5}


def test_loadkv_dict_to_pandas_reconstructs_split_dataframe(tmp_path):
    filename = tmp_path / "frame.h5"
    frame = pandas.DataFrame(
        data={"radius": [1.0, 2.5], "volume_fraction": [0.1, 0.2]},
        index=[10, 11],
    )

    storeKVPairs(filename, PurePosixPath("/frame"), frame.to_dict(orient="split").items())

    restored = loadKV(filename, PurePosixPath("/frame"), datatype="dictToPandas")

    pdt.assert_frame_equal(restored, frame)


def test_processing_data_round_trips_with_units_uncertainties_and_stage_selection(tmp_path):
    filename = tmp_path / "processing_data.h5"
    raw_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([1.0, 2.0], dtype=float),
                "I": np.array([10.0, 20.0], dtype=float),
                "ISigma": np.array([1.0, 2.0], dtype=float),
            }
        )
    )
    binned_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([1.5], dtype=float),
                "I": np.array([15.0], dtype=float),
                "ISigma": np.array([1.5], dtype=float),
            }
        )
    )
    raw_bundle.description = "input data"
    raw_bundle.default_plot = "signal"
    processing = ProcessingData()
    processing[STAGE_RAW] = raw_bundle
    processing[STAGE_BINNED] = binned_bundle
    setattr(processing, "analysis_stage", STAGE_BINNED)

    storeProcessingData(filename, PurePosixPath("/mcdata/processingData"), processing)
    restored = loadProcessingData(filename, PurePosixPath("/mcdata/processingData"))

    assert getattr(restored, "analysis_stage") == STAGE_BINNED
    assert restored[STAGE_RAW].default_plot == "signal"
    assert restored[STAGE_RAW].description == "input data"
    np.testing.assert_allclose(restored[STAGE_RAW]["Q"].signal, np.array([1.0, 2.0]))
    np.testing.assert_allclose(restored[STAGE_RAW]["signal"].signal, np.array([10.0, 20.0]))
    np.testing.assert_allclose(
        restored[STAGE_RAW]["signal"].uncertainties["propagate_to_all"],
        np.array([1.0, 2.0]),
    )
    assert restored[STAGE_RAW]["signal"].units == DEFAULT_INTENSITY_UNITS
