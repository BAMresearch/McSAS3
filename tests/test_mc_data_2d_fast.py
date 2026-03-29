import h5py
import numpy as np
import pytest

from mcsas3.data_adapters import STAGE_BINNED, STAGE_CLIPPED, STAGE_RAW, analysis_data_from_bundle
from mcsas3.mc_data_2d import McData2D


def _combined_uncertainty(data) -> np.ndarray:
    variance = np.zeros_like(np.asarray(data.signal, dtype=float), dtype=float)
    for uncertainty in data.uncertainties.values():
        variance += np.asarray(uncertainty, dtype=float) ** 2
    return np.sqrt(variance)


def _write_test_2d_nexus(filename):
    qx = np.array([[-0.5, 0.5], [-0.5, 0.5]], dtype=float)
    qy = np.array([[-0.5, -0.5], [0.5, 0.5]], dtype=float)
    q = np.stack([qy, qx, np.zeros_like(qx)], axis=0)
    intensity = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=float)
    sigma = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float)
    mask = np.array([[False, True], [False, False]], dtype=bool)

    with h5py.File(filename, "w") as h5f:
        h5f.attrs["default"] = "entry"
        entry = h5f.create_group("entry")
        entry.attrs["default"] = "data"
        data = entry.create_group("data")
        data.attrs["signal"] = "I"
        data.attrs["I_uncertainty"] = "I_unc"
        data.attrs["mask"] = "mask"
        data.attrs["axes"] = np.array(["q"], dtype="S")
        signal = data.create_dataset("I", data=intensity)
        signal.attrs["units"] = "1 / centimeter / steradian"
        sigma_ds = data.create_dataset("I_unc", data=sigma)
        sigma_ds.attrs["units"] = "1 / centimeter / steradian"
        q_ds = data.create_dataset("q", data=q)
        q_ds.attrs["units"] = "1 / angstrom"
        data.create_dataset("mask", data=mask)


def _make_test_mcdata2d(**kwargs):
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0

    data = McData2D(
        dataRange=[0.0, 1.0],
        orthoQ0Range=[0.0, 1.0],
        orthoQ1Range=[0.0, 1.0],
        qNudge=[0.1, -0.2],
        **kwargs,
    )
    data.from_stage(
        {
            "Qx": qx,
            "Qy": qy,
            "I": intensity,
            "ISigma": sigma,
            "mask": mask,
        }
    )
    return data


def test_mcdata2d_from_stage_builds_processing_without_manual_compatibility_mutation():
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    data = McData2D(dataRange=[0.0, 1.0], orthoQ0Range=[0.0, 1.0], orthoQ1Range=[0.0, 1.0], nbins=0)

    data.from_stage(
        {
            "Qx": qx,
            "Qy": qy,
            "I": intensity,
            "ISigma": sigma,
            "mask": mask,
        }
    )

    processing = data.to_processing_data()

    assert processing is data.processingData
    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}


def test_mcdata2d_prepare_requires_canonical_raw_stage():
    with pytest.raises(ValueError, match="canonical raw stage"):
        McData2D().prepare()


def test_mcdata2d_raw_stage_assignment_is_not_supported():
    with pytest.raises(AttributeError):
        McData2D().rawData2D = {
            "Qx": np.array([[0.0]]),
            "Qy": np.array([[0.0]]),
            "I": np.array([[1.0]]),
            "ISigma": np.array([[0.1]]),
        }


def test_mcdata2d_wrapper_only_loader_alias_methods_are_removed():
    data = McData2D()

    assert not hasattr(data, "from_pandas")
    assert not hasattr(data, "from_csv")
    assert not hasattr(data, "from_nexus")


def test_mcdata2d_removed_compatibility_view_attributes_are_absent():
    data = _make_test_mcdata2d()

    assert not hasattr(data, "rawData2D")
    assert not hasattr(data, "rawData")
    assert not hasattr(data, "clippedData")
    assert not hasattr(data, "binnedData")


def test_mcdata2d_dataframe_input_is_not_supported():
    with pytest.raises(TypeError, match="does not accept dataframe input"):
        McData2D(df=np.array([[1.0]]))


def test_mcdata2d_normalizes_declared_source_units_at_ingestion():
    coords = np.array([-0.15, -0.05, 0.05, 0.15], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4) / 100.0
    sigma = np.ones((4, 4), dtype=float) / 100.0
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0

    data = McData2D(
        dataRange=[0.0, 1.0],
        orthoQ0Range=[0.0, 1.0],
        orthoQ1Range=[0.0, 1.0],
        nbins=0,
        sourceQUnits="1 / angstrom",
        sourceIntensityUnits="1 / centimeter / steradian",
    )
    data.from_stage(
        {
            "Qx": qx,
            "Qy": qy,
            "I": intensity,
            "ISigma": sigma,
            "mask": mask,
        }
    )

    processing = data.to_processing_data()
    np.testing.assert_allclose(processing[STAGE_RAW]["Qx"].signal[0], np.array([-1.5, -0.5, 0.5, 1.5]))
    np.testing.assert_allclose(processing[STAGE_RAW]["signal"].signal.flatten()[:4], np.array([0.0, 1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(analysis_data_from_bundle(processing[STAGE_CLIPPED])["I"], np.array([9.0, 10.0]))


def test_mcdata2d_prepare_clips_filters_mask_and_applies_q_nudge():
    data = _make_test_mcdata2d()
    clipped_bundle = data.to_processing_data()[STAGE_CLIPPED]
    analysis_data = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)

    assert clipped_bundle["signal"].signal.shape == (2, 2)
    np.testing.assert_array_equal(clipped_bundle["mask"].signal, np.array([[True, False], [False, False]]))
    np.testing.assert_array_equal(_combined_uncertainty(clipped_bundle["signal"]), np.array([[1.0, 0.0], [1.0, 1.0]]))
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([0.6, 0.6]))
    np.testing.assert_allclose(analysis_data["Q"][1], np.array([-0.7, 0.3]))
    np.testing.assert_array_equal(analysis_data["I"], np.array([9.0, 10.0]))


def test_mcdata2d_from_file_uses_shared_ingestion_and_normalizes_units(tmp_path):
    filename = tmp_path / "input_2d.nxs"
    _write_test_2d_nexus(filename)

    data = McData2D(
        filename=filename,
        dataRange=[0.0, 10.0],
        orthoQ0Range=[0.0, 10.0],
        orthoQ1Range=[0.0, 10.0],
        nbins=0,
    )

    processing = data.to_processing_data()
    np.testing.assert_allclose(processing[STAGE_RAW]["Qx"].signal, np.array([[-5.0, 5.0], [-5.0, 5.0]]))
    np.testing.assert_allclose(processing[STAGE_RAW]["Qy"].signal, np.array([[-5.0, -5.0], [5.0, 5.0]]))
    np.testing.assert_allclose(processing[STAGE_RAW]["signal"].signal, np.array([[100.0, 200.0], [300.0, 400.0]]))
    np.testing.assert_array_equal(
        processing[STAGE_CLIPPED]["signal"].signal,
        np.array([[100.0, 200.0], [300.0, 400.0]]),
    )


def test_mcdata2d_reconstruct2d_restores_values_into_unmasked_pixels():
    data = _make_test_mcdata2d()

    reconstructed = data.reconstruct2D(np.array([100.0, 200.0]))

    assert reconstructed.shape == (2, 2)
    assert np.isnan(reconstructed[0, 0])
    assert np.isnan(reconstructed[0, 1])
    np.testing.assert_allclose(reconstructed[1], np.array([100.0, 200.0]))


def test_mcdata2d_rebin_creates_detached_binned_data_dict():
    data = _make_test_mcdata2d()
    processing = data.to_processing_data()

    assert processing[STAGE_BINNED] is not processing[STAGE_CLIPPED]
    np.testing.assert_array_equal(processing[STAGE_BINNED]["signal"].signal, processing[STAGE_CLIPPED]["signal"].signal)


def test_mcdata2d_store_and_load_restores_2d_state(tmp_path):
    filename = tmp_path / "mcdata_2d_state.h5"
    original = _make_test_mcdata2d()
    original.store(filename=filename)

    with h5py.File(filename, "r") as h5f:
        assert "/analyses/MCResult1/mcdata/measData" not in h5f
        assert "/analyses/MCResult1/mcdata/processingData/sample_raw/Qx/signal" in h5f
        assert "/analyses/MCResult1/mcdata/processingData/sample_clipped/signal/signal" in h5f
        assert "/analyses/MCResult1/mcdata/rawData" not in h5f
        assert "/analyses/MCResult1/mcdata/rawData2D" not in h5f
        assert "/analyses/MCResult1/mcdata/clippedData" not in h5f
        assert "/analyses/MCResult1/mcdata/binnedData" not in h5f

    restored = McData2D(loadFromFile=filename)
    original_processing = original.to_processing_data()
    restored_processing = restored.to_processing_data()

    np.testing.assert_allclose(restored.qNudge, original.qNudge)
    np.testing.assert_allclose(restored.orthoQ0Range, original.orthoQ0Range)
    np.testing.assert_allclose(restored.orthoQ1Range, original.orthoQ1Range)
    for stage_name in (STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED):
        np.testing.assert_array_equal(
            restored_processing[stage_name]["signal"].signal,
            original_processing[stage_name]["signal"].signal,
        )
    np.testing.assert_array_equal(
        restored_processing[STAGE_RAW]["Qx"].signal,
        original_processing[STAGE_RAW]["Qx"].signal,
    )
    restored_analysis_data = analysis_data_from_bundle(restored.to_analysis_bundle(), q_nudge=restored.qNudge)
    original_analysis_data = analysis_data_from_bundle(original.to_analysis_bundle(), q_nudge=original.qNudge)
    np.testing.assert_allclose(restored_analysis_data["Q"][0], original_analysis_data["Q"][0])
    np.testing.assert_allclose(restored_analysis_data["Q"][1], original_analysis_data["Q"][1])


def test_mcdata2d_processing_data_is_the_canonical_stage_store():
    data = _make_test_mcdata2d()

    processing = data.to_processing_data()

    assert data.processingData is processing
    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    assert processing[STAGE_BINNED] is not processing[STAGE_CLIPPED]
    np.testing.assert_allclose(processing[STAGE_RAW]["Qx"].signal[0], np.array([-1.5, -0.5, 0.5, 1.5]))
    analysis_data = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([0.6, 0.6]))
    np.testing.assert_allclose(analysis_data["Q"][1], np.array([-0.7, 0.3]))


def test_mcdata2d_analysis_stage_selects_the_bundle_to_fit():
    data = _make_test_mcdata2d()

    data.analysisStage = STAGE_CLIPPED
    processing = data.to_processing_data()

    assert data.analysisStage == STAGE_CLIPPED
    assert getattr(processing, "analysis_stage") == STAGE_CLIPPED
    assert data.to_analysis_bundle() is processing[STAGE_CLIPPED]
