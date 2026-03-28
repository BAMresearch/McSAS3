import numpy as np
import pandas
import pandas.testing as pdt

from mcsas3.data_adapters import (
    DEFAULT_INTENSITY_UNITS,
    DEFAULT_Q_UNITS,
    STAGE_BINNED,
    STAGE_CLIPPED,
    STAGE_RAW,
    bundle_from_1d_dataframe,
    bundle_from_2d_stage,
    legacy_dataframe_from_bundle,
    legacy_measdata_from_bundle,
)
from mcsas3.data_model import (
    MODACOR_IMPORT_MODE,
    BaseData,
    DataBundle,
    ProcessingData,
    ureg,
)
from mcsas3.mc_data_1d import McData1D
from mcsas3.mc_data_2d import McData2D


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


def test_1d_bundle_adapter_round_trips_dataframe_and_legacy_measdata():
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

    measdata = legacy_measdata_from_bundle(bundle, q_nudge=0.25)
    np.testing.assert_allclose(measdata["Q"][0], np.array([0.75, 1.25, 2.25]))
    np.testing.assert_allclose(measdata["I"], frame["I"].to_numpy())
    np.testing.assert_allclose(measdata["ISigma"], frame["ISigma"].to_numpy())

    pdt.assert_frame_equal(legacy_dataframe_from_bundle(bundle), frame)


def test_2d_bundle_adapter_builds_canonical_bundle_and_filters_legacy_measdata():
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

    measdata = legacy_measdata_from_bundle(bundle, q_nudge=[0.1, -0.2])
    np.testing.assert_allclose(measdata["Q"][0], np.array([0.6, 0.6]))
    np.testing.assert_allclose(measdata["Q"][1], np.array([-0.7, 0.3]))
    np.testing.assert_allclose(measdata["I"], np.array([9.0, 10.0]))
    np.testing.assert_allclose(measdata["ISigma"], np.array([1.0, 1.0]))

    frame = legacy_dataframe_from_bundle(bundle)
    assert list(frame.columns) == ["Qx", "Qy", "I", "ISigma", "mask"]
    assert len(frame) == 4


def test_mcdata1d_to_processing_data_matches_existing_binned_measdata():
    frame = pandas.DataFrame(
        {
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

    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    bridged = legacy_measdata_from_bundle(processing[STAGE_BINNED], q_nudge=data.qNudge)
    np.testing.assert_allclose(bridged["Q"][0], data.measData["Q"][0])
    np.testing.assert_allclose(bridged["I"], data.measData["I"])
    np.testing.assert_allclose(bridged["ISigma"], data.measData["ISigma"])


def test_mcdata2d_to_processing_data_matches_existing_binned_measdata():
    data = _make_test_mcdata2d()

    processing = data.to_processing_data()

    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    bridged = legacy_measdata_from_bundle(processing[STAGE_BINNED], q_nudge=data.qNudge)
    np.testing.assert_allclose(bridged["Q"][0], data.measData["Q"][0])
    np.testing.assert_allclose(bridged["Q"][1], data.measData["Q"][1])
    np.testing.assert_allclose(bridged["I"], data.measData["I"])
    np.testing.assert_allclose(bridged["ISigma"], data.measData["ISigma"])
