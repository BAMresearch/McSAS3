import numpy as np
import pandas
import pytest

from mcsas3.data_adapters import analysis_data_from_bundle
from mcsas3.mc_hat import McHat
from mcsas3.optimizer_input import OptimizerInput, optimizer_input_from_analysis_data, optimizer_input_from_bundle
from mcsas3.workflows import prepare_1d_processing_data, prepare_2d_processing_data


def _make_test_processing_2d(**kwargs):
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0

    return prepare_2d_processing_data(
        {
            "Qx": qx,
            "Qy": qy,
            "I": intensity,
            "ISigma": sigma,
            "mask": mask,
        },
        data_range=[0.0, 1.0],
        ortho_q0_range=[0.0, 1.0],
        ortho_q1_range=[0.0, 1.0],
        **kwargs,
    )


def test_optimizer_input_from_1d_bundle_matches_analysis_data():
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
    bundle = processing["sample_binned"]

    optimizer_input = optimizer_input_from_bundle(bundle)
    analysis_data = analysis_data_from_bundle(bundle)

    np.testing.assert_allclose(optimizer_input.q[0], analysis_data["Q"][0])
    np.testing.assert_allclose(optimizer_input.i, analysis_data["I"])
    np.testing.assert_allclose(optimizer_input.isigma, analysis_data["ISigma"])


def test_optimizer_input_from_2d_bundle_matches_analysis_data():
    processing = _make_test_processing_2d(nbins=0)
    bundle = processing["sample_binned"]

    optimizer_input = optimizer_input_from_bundle(bundle)
    analysis_data = analysis_data_from_bundle(bundle)

    np.testing.assert_allclose(optimizer_input.q[0], analysis_data["Q"][0])
    np.testing.assert_allclose(optimizer_input.q[1], analysis_data["Q"][1])
    np.testing.assert_allclose(optimizer_input.i, analysis_data["I"])
    np.testing.assert_allclose(optimizer_input.isigma, analysis_data["ISigma"])


def test_optimizer_input_from_bundle_and_analysis_data_path_agree_for_1d_bundle():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.5, 1.0, 2.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0], dtype=float),
        }
    )
    processing = prepare_1d_processing_data(frame, nbins=0)
    bundle = processing["sample_binned"]

    from_bundle = optimizer_input_from_bundle(bundle)
    from_analysis_data = optimizer_input_from_analysis_data(analysis_data_from_bundle(bundle))

    assert isinstance(from_bundle, OptimizerInput)
    np.testing.assert_allclose(from_bundle.q[0], from_analysis_data.q[0])
    np.testing.assert_allclose(from_bundle.i, from_analysis_data.i)
    np.testing.assert_allclose(from_bundle.isigma, from_analysis_data.isigma)


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


def test_optimizer_input_from_analysis_data_rejects_non_sequence_q():
    with pytest.raises(TypeError, match="Analysis data 'Q' must be a numpy array or a sequence of arrays"):
        optimizer_input_from_analysis_data(
            {
                "Q": 1.0,
                "I": np.array([1.0], dtype=float),
                "ISigma": np.array([0.1], dtype=float),
            }
        )
