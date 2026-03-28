import numpy as np
import pandas
import pandas.testing as pdt

from mcsas3.mc_data_1d import McData1D


def test_mcdata1d_prepare_applies_clip_omit_and_q_nudge_without_rebin():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
        }
    )

    data = McData1D(
        df=frame,
        dataRange=[1.0, 5.0],
        omitQRanges=[[1.5, 3.0]],
        nbins=0,
        qNudge=0.25,
    )

    expected = frame.iloc[[1, 3]].reset_index(drop=True)
    pdt.assert_frame_equal(data.clippedData.reset_index(drop=True), expected)
    pdt.assert_frame_equal(data.binnedData.reset_index(drop=True), expected)
    np.testing.assert_allclose(data.measData["Q"][0], np.array([1.25, 4.25]))
    np.testing.assert_allclose(data.measData["I"], expected["I"].to_numpy())
    np.testing.assert_allclose(data.measData["ISigma"], expected["ISigma"].to_numpy())


def test_mcdata1d_rebin_handles_multi_point_and_single_point_bins():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0, 2.0, 20.0], dtype=float),
            "I": np.array([10.0, 14.0, 100.0], dtype=float),
            "ISigma": np.array([1.0, 1.0, 2.0], dtype=float),
        }
    )

    data = McData1D(df=frame, nbins=2, IEmin=0.1)

    assert len(data.binnedData) == 2

    first_bin = data.binnedData.iloc[0]
    second_bin = data.binnedData.iloc[1]

    np.testing.assert_allclose(first_bin["Q"], 1.5)
    np.testing.assert_allclose(first_bin["I"], 12.0)
    np.testing.assert_allclose(first_bin["ISigma"], 2.0)
    np.testing.assert_allclose(first_bin["QSigma"], 0.5)

    np.testing.assert_allclose(second_bin["Q"], 20.0)
    np.testing.assert_allclose(second_bin["I"], 100.0)
    np.testing.assert_allclose(second_bin["ISigma"], 10.0)
    np.testing.assert_allclose(second_bin["QSigma"], 0.2)


def test_mcdata1d_store_and_load_restores_processed_state(tmp_path):
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
        }
    )
    filename = tmp_path / "mcdata_state.h5"

    original = McData1D(
        df=frame,
        dataRange=[1.0, 5.0],
        omitQRanges=[[1.5, 3.0]],
        nbins=0,
        qNudge=0.25,
    )
    original.store(filename=filename)

    restored = McData1D(loadFromFile=filename)

    pdt.assert_frame_equal(
        restored.rawData[original.rawData.columns].reset_index(drop=True),
        original.rawData.reset_index(drop=True),
    )
    pdt.assert_frame_equal(
        restored.clippedData[original.clippedData.columns].reset_index(drop=True),
        original.clippedData.reset_index(drop=True),
    )
    pdt.assert_frame_equal(
        restored.binnedData[original.binnedData.columns].reset_index(drop=True),
        original.binnedData.reset_index(drop=True),
    )
    np.testing.assert_allclose(restored.measData["Q"][0], original.measData["Q"][0])
    np.testing.assert_allclose(restored.measData["I"], original.measData["I"])
    np.testing.assert_allclose(restored.measData["ISigma"], original.measData["ISigma"])
    assert restored.qNudge == original.qNudge
