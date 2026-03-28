from pathlib import Path, PurePosixPath

import numpy as np
import pandas
import pandas.testing as pdt

from mcsas3.mc_hdf import ResultIndex, loadKV, storeKV, storeKVPairs


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
