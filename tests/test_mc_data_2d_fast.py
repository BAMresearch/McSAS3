import h5py
import numpy as np
import pandas

from mcsas3.data_adapters import STAGE_BINNED, STAGE_CLIPPED, STAGE_RAW, analysis_data_from_bundle
from mcsas3.mc_data_2d import McData2D


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
    data.rawData2D = {
        "Qx": qx,
        "Qy": qy,
        "I": intensity,
        "ISigma": sigma,
        "mask": mask,
    }
    data.rawData = pandas.DataFrame(
        {
            "Qx": qx.flatten(),
            "Qy": qy.flatten(),
            "I": intensity.flatten(),
            "ISigma": sigma.flatten(),
            "mask": mask.flatten(),
        }
    )
    data.prepare()
    return data


def test_mcdata2d_prepare_clips_filters_mask_and_applies_q_nudge():
    data = _make_test_mcdata2d()
    analysis_data = analysis_data_from_bundle(data.to_analysis_bundle(), q_nudge=data.qNudge)

    assert data.clippedData["I2D"].shape == (2, 2)
    np.testing.assert_array_equal(data.clippedData["kansas"], (2, 2))
    np.testing.assert_array_equal(data.clippedData["I"], np.array([9.0, 10.0]))
    np.testing.assert_array_equal(data.clippedData["ISigma"], np.array([1.0, 1.0]))
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([0.6, 0.6]))
    np.testing.assert_allclose(analysis_data["Q"][1], np.array([-0.7, 0.3]))
    np.testing.assert_array_equal(analysis_data["I"], np.array([9.0, 10.0]))


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
    data.rawData2D = {
        "Qx": qx,
        "Qy": qy,
        "I": intensity,
        "ISigma": sigma,
        "mask": mask,
    }
    data.rawData = pandas.DataFrame(
        {
            "Qx": qx.flatten(),
            "Qy": qy.flatten(),
            "I": intensity.flatten(),
            "ISigma": sigma.flatten(),
            "mask": mask.flatten(),
        }
    )
    data.prepare()

    np.testing.assert_allclose(data.rawData2D["Qx"][0], np.array([-1.5, -0.5, 0.5, 1.5]))
    np.testing.assert_allclose(data.rawData["I"].to_numpy()[:4], np.array([0.0, 1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(data.clippedData["I"], np.array([9.0, 10.0]))


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

    np.testing.assert_allclose(data.rawData2D["Qx"], np.array([[-5.0, 5.0], [-5.0, 5.0]]))
    np.testing.assert_allclose(data.rawData2D["Qy"], np.array([[-5.0, -5.0], [5.0, 5.0]]))
    np.testing.assert_allclose(data.rawData2D["I"], np.array([[100.0, 200.0], [300.0, 400.0]]))
    np.testing.assert_array_equal(data.clippedData["I2D"], np.array([[100.0, 200.0], [300.0, 400.0]]))


def test_mcdata2d_reconstruct2d_restores_values_into_unmasked_pixels():
    data = _make_test_mcdata2d()

    reconstructed = data.reconstruct2D(np.array([100.0, 200.0]))

    assert reconstructed.shape == (2, 2)
    assert np.isnan(reconstructed[0, 0])
    assert np.isnan(reconstructed[0, 1])
    np.testing.assert_allclose(reconstructed[1], np.array([100.0, 200.0]))


def test_mcdata2d_rebin_creates_detached_binned_data_dict():
    data = _make_test_mcdata2d()

    assert data.binnedData is not data.clippedData
    np.testing.assert_array_equal(data.binnedData["I"], data.clippedData["I"])


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

    assert restored.is2D()
    np.testing.assert_allclose(restored.qNudge, original.qNudge)
    np.testing.assert_allclose(restored.orthoQ0Range, original.orthoQ0Range)
    np.testing.assert_allclose(restored.orthoQ1Range, original.orthoQ1Range)
    np.testing.assert_array_equal(restored.rawData2D["I"], original.rawData2D["I"])
    np.testing.assert_array_equal(restored.rawData2D["Qx"], original.rawData2D["Qx"])
    np.testing.assert_array_equal(restored.clippedData["I"], original.clippedData["I"])
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

    raw_qx = processing[STAGE_RAW]["Qx"].signal.copy()
    data.rawData2D["Qx"][0, 0] = -999.0

    np.testing.assert_allclose(processing[STAGE_RAW]["Qx"].signal, raw_qx)
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
