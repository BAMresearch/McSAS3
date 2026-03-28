from types import SimpleNamespace

import numpy as np
import pandas
import pytest

from mcsas3.mc_core import McCore
from mcsas3.mc_hat import McHat
from mcsas3.optimizer_input import OptimizerInput


def test_mchat_fill_fit_parameter_limits_uses_q_range_for_auto_limits():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )

    hat.fillFitParameterLimits(
        OptimizerInput(
            q=(np.array([0.1, 1.0], dtype=float),),
            i=np.array([1.0, 2.0], dtype=float),
            isigma=np.array([0.1, 0.2], dtype=float),
        )
    )

    np.testing.assert_allclose(hat._modelArgs["fitParameterLimits"]["radius"], [np.pi / 1.0, np.pi / 0.1])


def test_mchat_fill_fit_parameter_limits_rejects_zero_q_for_auto_limits():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )

    with pytest.raises(AssertionError, match="smallest Q value cannot be zero"):
        hat.fillFitParameterLimits(
            OptimizerInput(
                q=(np.array([0.0, 1.0], dtype=float),),
                i=np.array([1.0, 2.0], dtype=float),
                isigma=np.array([0.1, 0.2], dtype=float),
            )
        )


def test_mccore_accept_updates_parameter_set_and_optimizer_state():
    core = McCore.__new__(McCore)
    core._model = SimpleNamespace(
        nContrib=2,
        parameterSet=pandas.DataFrame(data={"radius": [1.0, 2.0]}),
        pickParameters={"radius": 9.0},
        volumes=np.array([10.0, 20.0], dtype=float),
    )
    core._opt = SimpleNamespace(
        step=3,
        modelI=np.array([1.0, 2.0], dtype=float),
        testModelI=np.array([3.0, 4.0], dtype=float),
        testModelV=99.0,
        x0=np.array([1.0, 0.0], dtype=float),
        testX0=np.array([2.0, 0.5], dtype=float),
        acceptedSteps=[0],
        acceptedGofs=[1.5],
        accepted=1,
        gof=0.5,
    )

    core.accept()

    assert core._model.parameterSet.loc[1, "radius"] == 9.0
    np.testing.assert_allclose(core._opt.modelI, np.array([3.0, 4.0]))
    assert core._model.volumes[1] == 99.0
    np.testing.assert_allclose(core._opt.x0, np.array([2.0, 0.5]))
    assert core._opt.accepted == 2
    assert core._opt.acceptedSteps == [0, 3]
    assert core._opt.acceptedGofs == [1.5, 0.5]
