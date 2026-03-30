import numpy as np
import pandas
import pandas.testing as pdt
import pytest

from mcsas3.data_adapters import (
    DEFAULT_ANALYSIS_STAGE,
    DEFAULT_INTENSITY_UNITS,
    DEFAULT_Q_UNITS,
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    analysis_data_from_bundle,
    bundle_from_1d_dataframe,
    bundle_from_2d_stage,
    frame_from_bundle,
    get_processing_analysis_stage,
    selected_bundle_from_processing,
    set_processing_analysis_stage,
)
from mcsas3.data_model import (
    MODACOR_IMPORT_MODE,
    BaseData,
    DataBundle,
    ProcessingData,
    ureg,
)
from mcsas3.workflows import prepare_1d_processing_data, prepare_2d_processing_data


def test_modacor_import_layer_exposes_real_types():
    assert MODACOR_IMPORT_MODE in {"installed", "workspace"}

    bundle = DataBundle()
    bundle["signal"] = BaseData(
        signal=np.array([1.0]),
        units=ureg.dimensionless,
        uncertainties={"propagate_to_all": np.array([0.1])},
        rank_of_data=1,
    )

    processing = ProcessingData()
    processing[STAGE_RAW] = bundle

    assert processing[STAGE_RAW]["signal"].signal.shape == (1,)


def test_1d_bundle_adapter_round_trips_dataframe_and_analysis_data():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.5, 1.0, 2.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0], dtype=float),
            "QSigma": np.array([0.05, 0.1, 0.2], dtype=float),
            "mask": np.array([False, True, False], dtype=bool),
        }
    )

    bundle = bundle_from_1d_dataframe(frame)

    assert bundle["signal"].units == DEFAULT_INTENSITY_UNITS
    assert bundle["Q"].units == DEFAULT_Q_UNITS

    analysis_data = analysis_data_from_bundle(bundle)
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([0.5, 1.0, 2.0]))
    np.testing.assert_allclose(analysis_data["I"], frame["I"].to_numpy())
    np.testing.assert_allclose(analysis_data["ISigma"], frame["ISigma"].to_numpy())

    pdt.assert_frame_equal(frame_from_bundle(bundle), frame)


def test_2d_bundle_adapter_builds_canonical_bundle_and_filters_analysis_data():
    stage = {
        "I2D": np.array([[5.0, 6.0], [9.0, 10.0]], dtype=float),
        "ISigma2D": np.array([[1.0, 0.0], [1.0, 1.0]], dtype=float),
        "Q0Crop2D": np.array([[-0.5, -0.5], [0.5, 0.5]], dtype=float),
        "Q1Crop2D": np.array([[-0.5, 0.5], [-0.5, 0.5]], dtype=float),
        "mask2D": np.array([[True, False], [False, False]], dtype=bool),
    }

    bundle = bundle_from_2d_stage(stage)

    assert bundle["signal"].units == DEFAULT_INTENSITY_UNITS
    assert bundle["Qx"].units == DEFAULT_Q_UNITS
    assert bundle["Qy"].units == DEFAULT_Q_UNITS

    analysis_data = analysis_data_from_bundle(bundle)
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([0.5, 0.5]))
    np.testing.assert_allclose(analysis_data["Q"][1], np.array([-0.5, 0.5]))
    np.testing.assert_allclose(analysis_data["I"], np.array([9.0, 10.0]))
    np.testing.assert_allclose(analysis_data["ISigma"], np.array([1.0, 1.0]))

    frame = frame_from_bundle(bundle)
    assert list(frame.columns) == ["Qx", "Qy", "I", "ISigma", "mask"]
    assert len(frame) == 4


def test_1d_bundle_adapter_normalizes_declared_source_units_to_canonical_defaults():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.1, 0.2], dtype=float),
            "I": np.array([1.0, 2.0], dtype=float),
            "ISigma": np.array([0.1, 0.2], dtype=float),
            "QSigma": np.array([0.01, 0.02], dtype=float),
        }
    )

    bundle = bundle_from_1d_dataframe(
        frame,
        source_q_units="1 / angstrom",
        source_intensity_units="1 / centimeter / steradian",
    )

    assert bundle["signal"].units == DEFAULT_INTENSITY_UNITS
    assert bundle["Q"].units == DEFAULT_Q_UNITS
    np.testing.assert_allclose(bundle["signal"].signal, np.array([100.0, 200.0]))
    np.testing.assert_allclose(bundle["signal"].uncertainties["propagate_to_all"], np.array([10.0, 20.0]))
    np.testing.assert_allclose(bundle["Q"].signal, np.array([1.0, 2.0]))
    np.testing.assert_allclose(bundle["Q"].uncertainties["propagate_to_all"], np.array([0.1, 0.2]))


def test_2d_bundle_adapter_normalizes_declared_source_units_to_canonical_defaults():
    stage = {
        "I2D": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "ISigma2D": np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float),
        "Q0Crop2D": np.array([[-0.05, -0.05], [0.05, 0.05]], dtype=float),
        "Q1Crop2D": np.array([[-0.05, 0.05], [-0.05, 0.05]], dtype=float),
        "mask2D": np.array([[False, False], [False, True]], dtype=bool),
    }

    bundle = bundle_from_2d_stage(
        stage,
        source_q_units="1/A",
        source_intensity_units="1 / centimeter / steradian",
    )

    assert bundle["signal"].units == DEFAULT_INTENSITY_UNITS
    assert bundle["Qx"].units == DEFAULT_Q_UNITS
    assert bundle["Qy"].units == DEFAULT_Q_UNITS
    np.testing.assert_allclose(bundle["signal"].signal, np.array([[100.0, 200.0], [300.0, 400.0]]))
    np.testing.assert_allclose(bundle["Qx"].signal, np.array([[-0.5, 0.5], [-0.5, 0.5]]))
    np.testing.assert_allclose(bundle["Qy"].signal, np.array([[-0.5, -0.5], [0.5, 0.5]]))


def test_2d_bundle_adapter_rejects_mismatched_component_shapes():
    stage = {
        "I2D": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "ISigma2D": np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float),
        "Q0Crop2D": np.array([[-0.05, -0.05], [0.05, 0.05]], dtype=float),
        "Q1Crop2D": np.array([[-0.05, 0.05]], dtype=float),
    }

    with pytest.raises(ValueError, match="q1 shape"):
        bundle_from_2d_stage(stage)


def test_prepare_1d_processing_data_matches_selected_binned_analysis_data():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
        }
    )
    processing = prepare_1d_processing_data(
        frame,
        data_range=[1.0, 5.0],
        omit_q_ranges=[[1.5, 3.0]],
        nbins=0,
    )

    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    bridged = analysis_data_from_bundle(processing[STAGE_BINNED])
    direct = analysis_data_from_bundle(selected_bundle_from_processing(processing))
    np.testing.assert_allclose(bridged["Q"][0], direct["Q"][0])
    np.testing.assert_allclose(bridged["I"], direct["I"])
    np.testing.assert_allclose(bridged["ISigma"], direct["ISigma"])


def test_prepare_2d_processing_data_matches_selected_binned_analysis_data():
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0
    processing = prepare_2d_processing_data(
        {"Qx": qx, "Qy": qy, "I": intensity, "ISigma": sigma, "mask": mask},
        data_range=[0.0, 1.0],
        ortho_q0_range=[0.0, 1.0],
        ortho_q1_range=[0.0, 1.0],
        nbins=0,
    )

    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    bridged = analysis_data_from_bundle(processing[STAGE_BINNED])
    direct = analysis_data_from_bundle(selected_bundle_from_processing(processing))
    np.testing.assert_allclose(bridged["Q"][0], direct["Q"][0])
    np.testing.assert_allclose(bridged["Q"][1], direct["Q"][1])
    np.testing.assert_allclose(bridged["I"], direct["I"])
    np.testing.assert_allclose(bridged["ISigma"], direct["ISigma"])


def test_processing_data_tracks_selected_analysis_stage():
    processing = ProcessingData()
    processing[STAGE_RAW] = DataBundle()
    processing[STAGE_CLIPPED] = DataBundle()
    processing[STAGE_BINNED] = DataBundle()

    assert get_processing_analysis_stage(processing) == DEFAULT_ANALYSIS_STAGE

    set_processing_analysis_stage(processing, STAGE_CLIPPED)

    assert get_processing_analysis_stage(processing) == STAGE_CLIPPED
    assert selected_bundle_from_processing(processing) is processing[STAGE_CLIPPED]
