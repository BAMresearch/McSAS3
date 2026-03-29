import h5py
import numpy as np
import pandas
import pandas.testing as pdt
import pytest

from mcsas3.data_adapters import STAGE_BINNED, STAGE_CLIPPED, STAGE_RAW, analysis_data_from_bundle
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
    analysis_data = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)
    pdt.assert_frame_equal(data.clippedData.reset_index(drop=True), expected)
    pdt.assert_frame_equal(data.binnedData.reset_index(drop=True), expected)
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([1.25, 4.25]))
    np.testing.assert_allclose(analysis_data["I"], expected["I"].to_numpy())
    np.testing.assert_allclose(analysis_data["ISigma"], expected["ISigma"].to_numpy())


def test_mcdata1d_normalizes_declared_source_units_at_ingestion():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.1, 0.2, 0.4], dtype=float),
            "I": np.array([1.0, 2.0, 4.0], dtype=float),
            "ISigma": np.array([0.1, 0.2, 0.4], dtype=float),
        }
    )

    data = McData1D(
        df=frame,
        nbins=0,
        sourceQUnits="1 / angstrom",
        sourceIntensityUnits="1 / centimeter / steradian",
    )

    np.testing.assert_allclose(data.rawData["Q"], np.array([1.0, 2.0, 4.0]))
    np.testing.assert_allclose(data.rawData["I"], np.array([100.0, 200.0, 400.0]))
    np.testing.assert_allclose(data.rawData["ISigma"], np.array([10.0, 20.0, 40.0]))


def test_mcdata1d_accepts_read_config_q_and_i_units_aliases():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.1, 0.2, 0.4], dtype=float),
            "I": np.array([1.0, 2.0, 4.0], dtype=float),
            "ISigma": np.array([0.1, 0.2, 0.4], dtype=float),
        }
    )

    data = McData1D(
        df=frame,
        nbins=0,
        QUnits="1 / angstrom",
        IUnits="1 / centimeter / steradian",
    )

    assert data.sourceQUnits == "1 / angstrom"
    assert data.sourceIntensityUnits == "1 / centimeter / steradian"
    np.testing.assert_allclose(data.rawData["Q"], np.array([1.0, 2.0, 4.0]))
    np.testing.assert_allclose(data.rawData["I"], np.array([100.0, 200.0, 400.0]))


def test_mcdata1d_accepts_snake_case_unit_aliases():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.1, 0.2], dtype=float),
            "I": np.array([1.0, 2.0], dtype=float),
            "ISigma": np.array([0.1, 0.2], dtype=float),
        }
    )

    data = McData1D(
        df=frame,
        nbins=0,
        Q_units="1 / angstrom",
        I_units="1 / centimeter / steradian",
    )

    assert data.sourceQUnits == "1 / angstrom"
    assert data.sourceIntensityUnits == "1 / centimeter / steradian"
    np.testing.assert_allclose(data.rawData["Q"], np.array([1.0, 2.0]))
    np.testing.assert_allclose(data.rawData["I"], np.array([100.0, 200.0]))


def test_mcdata1d_rejects_conflicting_unit_alias_values():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.1], dtype=float),
            "I": np.array([1.0], dtype=float),
            "ISigma": np.array([0.1], dtype=float),
        }
    )

    with pytest.raises(ValueError, match="sourceQUnits"):
        McData1D(
            df=frame,
            nbins=0,
            QUnits="1 / angstrom",
            sourceQUnits="1 / nanometer",
        )


def test_mcdata1d_to_processing_data_requires_canonical_state():
    with pytest.raises(ValueError, match="requires canonical processingData"):
        McData1D().to_processing_data()


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
    assert list(data.binnedData.columns) == ["Q", "I", "ISigma", "QSigma"]

    np.testing.assert_allclose(first_bin["Q"], 1.5)
    np.testing.assert_allclose(first_bin["I"], 12.0)
    np.testing.assert_allclose(first_bin["ISigma"], 2.0)
    np.testing.assert_allclose(first_bin["QSigma"], 0.5)

    np.testing.assert_allclose(second_bin["Q"], 20.0)
    np.testing.assert_allclose(second_bin["I"], 100.0)
    np.testing.assert_allclose(second_bin["ISigma"], 10.0)
    np.testing.assert_allclose(second_bin["QSigma"], 0.2)


def test_mcdata1d_compatibility_views_only_expose_canonical_columns():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0, 2.0, 20.0], dtype=float),
            "I": np.array([10.0, 14.0, 100.0], dtype=float),
            "ISigma": np.array([1.0, 1.0, 2.0], dtype=float),
            "Transmission": np.array([0.9, 0.8, 0.7], dtype=float),
        }
    )

    data = McData1D(df=frame, nbins=2, IEmin=0.1)

    assert list(data.rawData.columns) == ["Q", "I", "ISigma"]
    assert list(data.clippedData.columns) == ["Q", "I", "ISigma"]
    assert list(data.binnedData.columns) == ["Q", "I", "ISigma", "QSigma"]


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
        dataRange=[10.0, 50.0],
        omitQRanges=[[15.0, 30.0]],
        nbins=0,
        qNudge=0.25,
        sourceQUnits="1 / angstrom",
        sourceIntensityUnits="1 / centimeter / steradian",
    )
    original.store(filename=filename)

    with h5py.File(filename, "r") as h5f:
        assert "/analyses/MCResult1/mcdata/measData" not in h5f
        assert "/analyses/MCResult1/mcdata/processingData/sample_raw/signal/signal" in h5f
        assert "/analyses/MCResult1/mcdata/processingData/sample_binned/Q/signal" in h5f
        assert "/analyses/MCResult1/mcdata/rawData" not in h5f
        assert "/analyses/MCResult1/mcdata/clippedData" not in h5f
        assert "/analyses/MCResult1/mcdata/binnedData" not in h5f

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
    restored_analysis_data = analysis_data_from_bundle(restored.to_analysis_bundle(), q_nudge=restored.qNudge)
    original_analysis_data = analysis_data_from_bundle(original.to_analysis_bundle(), q_nudge=original.qNudge)
    np.testing.assert_allclose(restored_analysis_data["Q"][0], original_analysis_data["Q"][0])
    np.testing.assert_allclose(restored_analysis_data["I"], original_analysis_data["I"])
    np.testing.assert_allclose(restored_analysis_data["ISigma"], original_analysis_data["ISigma"])
    np.testing.assert_allclose(original.rawData["Q"], np.array([5.0, 10.0, 20.0, 40.0, 50.0]))
    np.testing.assert_allclose(original.rawData["I"], np.array([500.0, 1000.0, 2000.0, 4000.0, 5000.0]))
    assert restored.sourceQUnits == original.sourceQUnits
    assert restored.sourceIntensityUnits == original.sourceIntensityUnits
    assert restored.qNudge == original.qNudge


def test_mcdata1d_from_nexus_detects_and_normalizes_dataset_units(tmp_path):
    filename = tmp_path / "unitized_input.nxs"

    with h5py.File(filename, "w") as h5f:
        h5f.attrs["default"] = "entry"
        entry = h5f.create_group("entry")
        entry.attrs["default"] = "data"
        data = entry.create_group("data")
        data.attrs["signal"] = "I"
        data.attrs["I_uncertainty"] = "I_unc"
        data.attrs["axes"] = np.array(["q"], dtype="S")
        signal = data.create_dataset("I", data=np.array([1.0, 2.0, 4.0], dtype=float))
        signal.attrs["units"] = "1 / centimeter / steradian"
        sigma = data.create_dataset("I_unc", data=np.array([0.1, 0.2, 0.4], dtype=float))
        sigma.attrs["units"] = "1 / centimeter / steradian"
        q = data.create_dataset("q", data=np.array([0.1, 0.2, 0.4], dtype=float))
        q.attrs["units"] = "1 / angstrom"

    loaded = McData1D(filename=filename, nbins=0)

    assert loaded.sourceQUnits == "1 / angstrom"
    assert loaded.sourceIntensityUnits == "1 / centimeter / steradian"
    np.testing.assert_allclose(loaded.rawData["Q"], np.array([1.0, 2.0, 4.0]))
    np.testing.assert_allclose(loaded.rawData["I"], np.array([100.0, 200.0, 400.0]))
    np.testing.assert_allclose(loaded.rawData["ISigma"], np.array([10.0, 20.0, 40.0]))


def test_mcdata1d_load_requires_canonical_processing_data(tmp_path):
    filename = tmp_path / "legacy_only_mcdata_state.h5"

    with h5py.File(filename, "w") as h5f:
        h5f.require_group("/analyses/MCResult1/mcdata/rawData").create_dataset("Q", data=np.array([1.0]))

    with pytest.raises(ValueError, match="does not contain canonical processing data"):
        McData1D(loadFromFile=filename)


def test_mcdata1d_processing_data_is_the_canonical_stage_store():
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

    processing = data.to_processing_data()

    assert data.processingData is processing
    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}

    raw_q = processing[STAGE_RAW]["Q"].signal.copy()
    raw_view = data.rawData
    raw_view.loc[:, "Q"] = -999.0

    np.testing.assert_allclose(processing[STAGE_RAW]["Q"].signal, raw_q)
    analysis_data = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([1.25, 4.25]))


def test_mcdata1d_compatibility_views_are_rederived_on_access():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0, 2.0, 4.0], dtype=float),
            "I": np.array([10.0, 20.0, 40.0], dtype=float),
            "ISigma": np.array([1.0, 2.0, 4.0], dtype=float),
        }
    )
    data = McData1D(df=frame, nbins=0)

    raw_view = data.rawData
    raw_view.loc[:, "Q"] = -999.0

    np.testing.assert_allclose(data.rawData["Q"], np.array([1.0, 2.0, 4.0]))


def test_mcdata1d_analysis_stage_selects_the_bundle_to_fit():
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

    data.analysisStage = STAGE_CLIPPED
    processing = data.to_processing_data()

    assert data.analysisStage == STAGE_CLIPPED
    assert getattr(processing, "analysis_stage") == STAGE_CLIPPED
    assert data.to_analysis_bundle() is processing[STAGE_CLIPPED]

    bridged = analysis_data_from_bundle(processing[STAGE_CLIPPED], q_nudge=data.qNudge)
    direct = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)
    np.testing.assert_allclose(direct["Q"][0], bridged["Q"][0])
