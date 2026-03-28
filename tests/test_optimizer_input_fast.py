import numpy as np
import pandas

from mcsas3.mc_data_1d import McData1D
from mcsas3.mc_data_2d import McData2D
from mcsas3.mc_hat import McHat
from mcsas3.optimizer_input import OptimizerInput, optimizer_input_from_bundle, optimizer_input_from_legacy_measdata


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


def test_mcdata1d_to_optimizer_input_matches_legacy_measdata():
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

    optimizer_input = data.to_optimizer_input()

    np.testing.assert_allclose(optimizer_input.q[0], data.measData["Q"][0])
    np.testing.assert_allclose(optimizer_input.i, data.measData["I"])
    np.testing.assert_allclose(optimizer_input.isigma, data.measData["ISigma"])


def test_mcdata2d_to_optimizer_input_matches_legacy_measdata():
    data = _make_test_mcdata2d()

    optimizer_input = data.to_optimizer_input()

    np.testing.assert_allclose(optimizer_input.q[0], data.measData["Q"][0])
    np.testing.assert_allclose(optimizer_input.q[1], data.measData["Q"][1])
    np.testing.assert_allclose(optimizer_input.i, data.measData["I"])
    np.testing.assert_allclose(optimizer_input.isigma, data.measData["ISigma"])


def test_optimizer_input_from_bundle_and_legacy_path_agree_for_1d_bundle():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.5, 1.0, 2.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0], dtype=float),
        }
    )
    data = McData1D(df=frame, nbins=0, qNudge=0.25)
    bundle = data.to_processing_data()["sample_binned"]

    from_bundle = optimizer_input_from_bundle(bundle, q_nudge=data.qNudge)
    from_legacy = optimizer_input_from_legacy_measdata(data.measData)

    assert isinstance(from_bundle, OptimizerInput)
    np.testing.assert_allclose(from_bundle.q[0], from_legacy.q[0])
    np.testing.assert_allclose(from_bundle.i, from_legacy.i)
    np.testing.assert_allclose(from_bundle.isigma, from_legacy.isigma)


def test_mchat_fill_fit_parameter_limits_accepts_optimizer_input():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )
    optimizer_input = OptimizerInput(
        q=(np.array([0.1, 1.0], dtype=float),),
        i=np.array([1.0, 2.0], dtype=float),
        isigma=np.array([0.1, 0.2], dtype=float),
    )

    hat.fillFitParameterLimits(optimizer_input)

    np.testing.assert_allclose(hat._modelArgs["fitParameterLimits"]["radius"], [np.pi / 1.0, np.pi / 0.1])
