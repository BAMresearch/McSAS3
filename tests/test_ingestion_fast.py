import h5py
import numpy as np
import pandas
import pandas.testing as pdt
import pytest

from mcsas3.ingestion import DEFAULT_1D_CSVARGS, load_1d_dataframe_from_file


def test_load_1d_dataframe_from_csv_uses_default_columns(tmp_path):
    filename = tmp_path / "input.dat"
    filename.write_text("0.1 1.0 0.1\n0.2 2.0 0.2\n")

    loaded = load_1d_dataframe_from_file(filename, csvargs=DEFAULT_1D_CSVARGS)

    assert loaded.loader == "from_csv"
    pdt.assert_frame_equal(
        loaded.frame.reset_index(drop=True),
        pandas.DataFrame(
            {
                "Q": np.array([0.1, 0.2], dtype=float),
                "I": np.array([1.0, 2.0], dtype=float),
                "ISigma": np.array([0.1, 0.2], dtype=float),
            }
        ),
    )


def test_load_1d_dataframe_from_nexus_detects_units_and_follows_default_path(tmp_path):
    filename = tmp_path / "input.nxs"

    with h5py.File(filename, "w") as h5f:
        h5f.attrs["default"] = "entry"
        entry = h5f.create_group("entry")
        entry.attrs["default"] = "data"
        data = entry.create_group("data")
        data.attrs["signal"] = "I"
        data.attrs["I_uncertainty"] = "I_unc"
        data.attrs["axes"] = np.array(["q"], dtype="S")
        signal = data.create_dataset("I", data=np.array([1.0, 2.0], dtype=float))
        signal.attrs["units"] = "1 / centimeter / steradian"
        sigma = data.create_dataset("I_unc", data=np.array([0.1, 0.2], dtype=float))
        sigma.attrs["units"] = "1 / centimeter / steradian"
        q = data.create_dataset("q", data=np.array([0.1, 0.2], dtype=float))
        q.attrs["units"] = "1 / angstrom"

    loaded = load_1d_dataframe_from_file(filename)

    assert loaded.loader == "from_nexus"
    assert loaded.source_q_units == "1 / angstrom"
    assert loaded.source_intensity_units == "1 / centimeter / steradian"
    np.testing.assert_allclose(loaded.frame["Q"], np.array([0.1, 0.2]))
    np.testing.assert_allclose(loaded.frame["I"], np.array([1.0, 2.0]))


def test_load_1d_dataframe_from_nexus_rejects_2d_q_data(tmp_path):
    filename = tmp_path / "input_2d.nxs"

    with h5py.File(filename, "w") as h5f:
        h5f.attrs["default"] = "entry"
        entry = h5f.create_group("entry")
        entry.attrs["default"] = "data"
        data = entry.create_group("data")
        data.attrs["signal"] = "I"
        data.attrs["I_uncertainty"] = "I_unc"
        data.attrs["axes"] = np.array(["q"], dtype="S")
        data.create_dataset("I", data=np.ones((2, 2), dtype=float))
        data.create_dataset("I_unc", data=np.ones((2, 2), dtype=float))
        data.create_dataset("q", data=np.ones((2, 2), dtype=float))

    with pytest.raises(ValueError, match="cannot read 2D NeXus data directly"):
        load_1d_dataframe_from_file(filename)
