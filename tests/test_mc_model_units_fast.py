import numpy as np
import pytest
import sasmodels.direct_model

from mcsas3.mc_model import McModel


def test_mcsas3_to_sasmodels_unit_bridge_converts_size_parameters_and_q(monkeypatch):
    captured = {}

    class FakeSasModelsFunction:
        def make_kernel(self, q_arrays):
            captured["q_arrays"] = q_arrays
            return object()

    def fake_call_fq(kernel, parameters):
        captured["parameters"] = parameters
        return None, np.array([20.0]), None, np.array([4.0]), None

    monkeypatch.setattr(sasmodels.direct_model, "call_Fq", fake_call_fq)

    model = McModel.__new__(McModel)
    model.modelName = "sphere"
    model.func = FakeSasModelsFunction()
    model._sasmodels_length_parameters = frozenset({"radius", "length", "thick_shell"})
    model.staticParameters = {
        "background": 0.0,
        "scale": 1.0,
        "sld": 6.0,
        "sld_solvent": 1.0,
        "thick_shell": 2.0,
        "radius_effective_mode": 1,
        "radius_pd_type": "gaussian",
    }

    kernel = model.make_kernel([np.array([0.1, 1.0])])
    intensity, volume = model.calcModelIV({"radius": 35.0, "length": 120.0, "factor": 2.0})
    static_parameters = model.kernel_static_parameters()

    np.testing.assert_allclose(captured["q_arrays"][0], np.array([0.01, 0.1]))
    assert model.kernel is kernel
    assert static_parameters["thick_shell"] == pytest.approx(20.0)
    assert static_parameters["radius_pd_type"] == "gaussian"
    assert captured["parameters"]["radius"] == pytest.approx(350.0)
    assert captured["parameters"]["length"] == pytest.approx(1200.0)
    assert captured["parameters"]["thick_shell"] == pytest.approx(20.0)
    assert captured["parameters"]["factor"] == pytest.approx(2.0)
    assert captured["parameters"]["radius_effective_mode"] == 1
    assert captured["parameters"]["radius_pd_type"] == "gaussian"
    assert model.volume_fraction_correction_factor() == pytest.approx(0.01)
    np.testing.assert_allclose(intensity, np.array([5.0]))
    np.testing.assert_allclose(volume, np.array([4.0]))


def test_custom_models_keep_canonical_mcsas3_units():
    captured = {}

    class FakeCustomFunction:
        def make_kernel(self, q_arrays):
            captured["q_arrays"] = q_arrays
            return lambda **parameters: (np.array([6.0]), np.array([3.0]))

    model = McModel.__new__(McModel)
    model.modelName = "mcsas_sphere"
    model.func = FakeCustomFunction()
    model.staticParameters = {"background": 0.0, "scale": 1.0}

    model.make_kernel([np.array([0.1, 1.0])])
    intensity, volume = model.calcModelIV({"radius": 35.0})

    np.testing.assert_allclose(captured["q_arrays"][0], np.array([0.1, 1.0]))
    assert model.volume_fraction_correction_factor() == pytest.approx(1e-5)
    np.testing.assert_allclose(intensity, np.array([2.0]))
    np.testing.assert_allclose(volume, np.array([3.0]))
