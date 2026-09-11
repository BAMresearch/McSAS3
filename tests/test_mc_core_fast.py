import logging
from pathlib import Path
from types import SimpleNamespace

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas
import pytest
import sasmodels.core
import sasmodels.direct_model

from mcsas3.data_adapters import bundle_from_1d_dataframe
from mcsas3.mc_analysis import McAnalysis
from mcsas3.mc_core import McCore
from mcsas3.mc_hat import McHat
from mcsas3.mc_hdf import ResultIndex, storeKV
from mcsas3.mc_model import SIM_MODEL_EXTRAPOLATION_MIN_POINTS, McModel, McSimPseudoModel
from mcsas3.mc_model_histogrammer import McModelHistogrammer
from mcsas3.mc_opt import McOpt
from mcsas3.mc_plot import _plot_background_intensity
from mcsas3.osb import (
    POROD_FIT_PARAMETER_NAMES,
    background_intensity,
    fitted_intensity,
    optimizeScalingAndBackground,
)


def test_mchat_fill_fit_parameter_limits_uses_q_range_for_auto_limits():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )

    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([0.1, 1.0], dtype=float),
                "I": np.array([1.0, 2.0], dtype=float),
                "ISigma": np.array([0.1, 0.2], dtype=float),
            }
        )
    )

    hat.fillFitParameterLimits(analysis_bundle)

    np.testing.assert_allclose(hat._modelArgs["fitParameterLimits"]["radius"], [np.pi / 1.0, 2 * np.pi / 0.1])


def test_mchat_fill_fit_parameter_limits_rejects_zero_q_for_auto_limits():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )

    with pytest.raises(ValueError, match="smallest Q value must be > 0"):
        hat.fillFitParameterLimits(
            bundle_from_1d_dataframe(
                pandas.DataFrame(
                    {
                        "Q": np.array([0.0, 1.0], dtype=float),
                        "I": np.array([1.0, 2.0], dtype=float),
                        "ISigma": np.array([0.1, 0.2], dtype=float),
                    }
                )
            )
        )


def test_mchat_fill_fit_parameter_limits_rejects_unknown_string_limit_mode():
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "invalid"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )

    with pytest.raises(ValueError, match='explicit \\[min, max\\] pairs or the string "auto"'):
        hat.fillFitParameterLimits(
            bundle_from_1d_dataframe(
                pandas.DataFrame(
                    {
                        "Q": np.array([0.1, 1.0], dtype=float),
                        "I": np.array([1.0, 2.0], dtype=float),
                        "ISigma": np.array([0.1, 0.2], dtype=float),
                    }
                )
            )
        )


def test_mchat_init_rejects_unknown_option_key():
    with pytest.raises(ValueError, match="not a valid option"):
        McHat(modelName="mcsas_sphere", invalidOption=True)


def test_mchat_routes_porod_background_switch_to_optimizer_state():
    hat = McHat(modelName="mcsas_sphere", fitPorodBackground=True)

    assert hat._optArgs["fitPorodBackground"] is True


def test_mcanalysis_requires_existing_project_file(tmp_path):
    with pytest.raises(ValueError, match="project filename"):
        McAnalysis(
            tmp_path / "missing_result.h5",
            bundle_from_1d_dataframe(
                pandas.DataFrame(
                    {
                        "Q": np.array([0.1, 1.0], dtype=float),
                        "I": np.array([1.0, 2.0], dtype=float),
                        "ISigma": np.array([0.1, 0.2], dtype=float),
                    }
                )
            ),
            pandas.DataFrame(),
        )


def test_mcmodelhistogrammer_requires_core_instance_type():
    with pytest.raises(TypeError, match="core instance"):
        McModelHistogrammer(object(), pandas.DataFrame())


def test_mcmodelhistogrammer_does_not_mutate_input_hist_ranges():
    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([0.1, 0.2, 0.3], dtype=float),
                "I": np.array([1.0, 1.5, 2.0], dtype=float),
                "ISigma": np.array([0.1, 0.1, 0.2], dtype=float),
            }
        )
    )
    model = McModel(
        modelName="mcsas_sphere",
        nContrib=1,
        fitParameterLimits={"radius": (5.0, 10.0)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        seed=123,
    )
    opt = McOpt(convCrit=0.0, maxIter=1, repetition=0)
    core = McCore(analysis_input=analysis_bundle, model=model, opt=opt)
    hist_ranges = pandas.DataFrame(
        [
            dict(
                parameter="radius",
                nBin=4,
                binScale="linear",
                presetRangeMin=1.0,
                presetRangeMax=20.0,
                binWeighting="vol",
                autoRange=True,
            )
        ]
    )
    original_hist_ranges = hist_ranges.copy(deep=True)

    with pytest.warns(RuntimeWarning):
        histogrammer = McModelHistogrammer(core, hist_ranges)

    assert "rangeMin" not in hist_ranges.columns
    assert "rangeMax" not in hist_ranges.columns
    pandas.testing.assert_frame_equal(hist_ranges, original_hist_ranges)
    assert histogrammer._histRanges.loc[0, "rangeMin"] == 5.0
    assert histogrammer._histRanges.loc[0, "rangeMax"] == 10.0


def test_mcmodel_rejects_unknown_option_key():
    with pytest.raises(ValueError, match="not a valid settable option"):
        McModel(invalidOption=True)


def test_mcsim_pseudo_model_requires_simulation_arrays():
    with pytest.raises(ValueError, match="Missing: simDataQ1, simDataI, simDataISigma"):
        McSimPseudoModel(simDataQ0=np.array([0.1, 0.2], dtype=float))


def test_mcsim_pseudo_model_estimates_high_q_porod_extrapolation():
    q = np.linspace(1.0, 10.0, 20)
    intensity = 4.2 * q**-4
    model = McSimPseudoModel(
        simDataQ0=q,
        simDataQ1=None,
        simDataI=intensity,
        simDataISigma=np.full_like(q, 0.01),
    )

    assert model.extrapY0 == 0.0
    assert model.extrapScaling == pytest.approx(4.2)
    assert model.info.parameters.defaults["extrapY0"] == 0.0
    assert model.info.parameters.defaults["extrapScaling"] == pytest.approx(4.2)
    np.testing.assert_allclose(model.extrapolatorHighQ(np.array([20.0])), np.array([4.2 * 20.0**-4]))


def test_mcsim_pseudo_model_auto_extrapolation_includes_negative_tail_intensities():
    q = np.linspace(1.0, 10.0, 20)
    intensity = 4.2 * q**-4
    intensity[-1] = -0.01
    model = McSimPseudoModel(
        simDataQ0=q,
        simDataQ1=None,
        simDataI=intensity,
        simDataISigma=np.full_like(q, 0.01),
    )
    tail_q = q[-SIM_MODEL_EXTRAPOLATION_MIN_POINTS:]
    tail_intensity = intensity[-SIM_MODEL_EXTRAPOLATION_MIN_POINTS:]
    predictor = tail_q**-4
    expected_scaling = np.sum(predictor * tail_intensity) / np.sum(predictor**2)

    assert model.extrapScaling == pytest.approx(expected_scaling)


def test_mcsim_pseudo_model_keeps_explicit_high_q_extrapolation():
    q = np.linspace(1.0, 10.0, 20)
    model = McSimPseudoModel(
        extrapY0=1.5,
        extrapScaling=2.5,
        simDataQ0=q,
        simDataQ1=None,
        simDataI=4.2 * q**-4,
        simDataISigma=np.full_like(q, 0.01),
    )

    assert model.extrapY0 == 1.5
    assert model.extrapScaling == 2.5


def test_mcmodel_loads_sim_model_without_explicit_extrapolation_parameters():
    q = np.linspace(1.0, 10.0, 20)
    model = McModel(
        modelName="sim",
        nContrib=1,
        fitParameterLimits={"factor": (1.0, 2.0)},
        staticParameters={
            "simDataQ0": q,
            "simDataI": 4.2 * q**-4,
            "simDataISigma": np.full_like(q, 0.01),
        },
        seed=123,
    )

    assert model.staticParameters["simDataQ1"] is None
    assert model.staticParameters["extrapY0"] == 0.0
    assert model.staticParameters["extrapScaling"] == pytest.approx(4.2)


def test_mcopt_instances_do_not_share_accepted_history():
    first = McOpt()
    second = McOpt()

    first.acceptedSteps.append(5)
    first.acceptedGofs.append(0.25)

    assert second.acceptedSteps == []
    assert second.acceptedGofs == []


def test_mcopt_rejects_non_boolean_porod_switch():
    with pytest.raises(TypeError, match="fitPorodBackground.*bool"):
        McOpt(fitPorodBackground="true")


def test_mcsas_sphere_model_defaults_remain_available_via_model_info():
    model = McModel(
        modelName="mcsas_sphere",
        nContrib=1,
        fitParameterLimits={"radius": (5.0, 10.0)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        seed=123,
    )

    defaults = model.model_parameters()

    assert defaults["radius"] == 1
    assert defaults["scale"] == 1.0
    assert defaults["background"] == 0.0


def test_mcmodel_available_models_returns_grouped_mapping():
    model = McModel(
        modelName="mcsas_sphere",
        nContrib=1,
        fitParameterLimits={"radius": (5.0, 10.0)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        seed=123,
    )

    available = model.available_models()

    assert "one_dimensional" in available
    assert "one_and_two_dimensional" in available
    assert "sphere" in available["one_dimensional"] + available["one_and_two_dimensional"]


def test_mcmodel_model_parameters_requires_loaded_model():
    model = McModel.__new__(McModel)
    model.func = None

    with pytest.raises(RuntimeError, match="loaded before model parameters can be queried"):
        model.model_parameters()


def test_optimize_scaling_and_background_rejects_nan_measurement_data():
    with pytest.raises(ValueError, match="cannot contain NaN"):
        optimizeScalingAndBackground(
            measDataI=np.array([1.0, np.nan], dtype=float),
            measDataISigma=np.array([0.1, 0.1], dtype=float),
        )


def test_optimize_scaling_and_background_preserves_custom_bounds():
    custom_bounds = [[0.0, 10.0], [-2.0, 2.0]]

    optimizer = optimizeScalingAndBackground(
        measDataI=np.array([1.0, 2.0, 3.0], dtype=float),
        measDataISigma=np.array([0.1, 0.1, 0.1], dtype=float),
        xBounds=custom_bounds,
    )

    assert optimizer.xBounds == custom_bounds


def test_optimize_scaling_and_background_accepts_canonical_bundle_input():
    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([0.1, 0.2, 0.3], dtype=float),
                "I": np.array([1.0, 1.5, 2.0], dtype=float),
                "ISigma": np.array([0.1, 0.1, 0.2], dtype=float),
            }
        )
    )

    optimizer = optimizeScalingAndBackground(analysis_bundle)

    np.testing.assert_allclose(optimizer.measDataI, np.array([1.0, 1.5, 2.0]))
    np.testing.assert_allclose(optimizer.measDataISigma, np.array([0.1, 0.1, 0.2]))


def test_fitted_intensity_supports_legacy_and_porod_parameter_vectors():
    q = np.array([0.5, 1.0, 2.0], dtype=float)
    model_intensity = np.array([1.0, 2.0, 3.0], dtype=float)

    legacy_fit = fitted_intensity(model_intensity, [2.0, 0.5], q)
    porod_fit = fitted_intensity(model_intensity, [2.0, 0.5, 4.0], q)

    np.testing.assert_allclose(legacy_fit, 2.0 * model_intensity + 0.5)
    np.testing.assert_allclose(porod_fit, 2.0 * model_intensity + 0.5 + 4.0 * q**-4)
    np.testing.assert_allclose(background_intensity([2.0, 0.5], q), np.full_like(q, 0.5))
    np.testing.assert_allclose(background_intensity([2.0, 0.5, 4.0], q), 0.5 + 4.0 * q**-4)


def test_fitted_intensity_requires_positive_q_for_porod_parameters():
    with pytest.raises(ValueError, match="finite, strictly positive Q"):
        fitted_intensity(np.ones(2), [1.0, 0.0, 1.0], [0.0, 1.0])


def test_result_card_background_curve_is_grey_and_dotted():
    figure, _axes = plt.subplots()

    background_line = _plot_background_intensity([0.1, 0.2], [2.0, 0.5])

    assert background_line.get_label() == "Fitted background (flat + Porod)"
    assert background_line.get_color() == "0.5"
    assert background_line.get_linestyle() == ":"
    plt.close(figure)


def test_optimize_scaling_background_and_porod_recovers_synthetic_parameters():
    q = np.geomspace(0.02, 0.5, 100)
    model_intensity = np.exp(-5.0 * q)
    expected = np.array([2.3, 0.4, 1.7e-6])
    measured_intensity = fitted_intensity(model_intensity, expected, q)
    optimizer = optimizeScalingAndBackground(
        measured_intensity,
        np.full_like(q, 0.01),
        fitPorodBackground=True,
        measDataQ=q,
    )

    fitted_parameters, gof = optimizer.match(model_intensity)

    assert optimizer.parameterNames == POROD_FIT_PARAMETER_NAMES
    np.testing.assert_allclose(fitted_parameters, expected, rtol=2e-5, atol=1e-9)
    assert gof == pytest.approx(0.0, abs=2e-8)


def test_optimize_scaling_background_and_porod_enforces_non_negative_coefficient():
    q = np.geomspace(0.05, 1.0, 80)
    model_intensity = np.exp(-q)
    measured_intensity = 1.5 * model_intensity + 0.2 - 1e-7 * q**-4
    optimizer = optimizeScalingAndBackground(
        measured_intensity,
        np.full_like(q, 0.01),
        fitPorodBackground=True,
        measDataQ=q,
    )

    fitted_parameters, _gof = optimizer.match(model_intensity)

    assert fitted_parameters[2] >= 0.0
    assert fitted_parameters[2] == pytest.approx(0.0, abs=1e-12)


def test_optimize_scaling_background_and_porod_requires_q():
    with pytest.raises(ValueError, match="Measurement Q is required"):
        optimizeScalingAndBackground(
            np.array([1.0, 2.0]),
            np.array([0.1, 0.1]),
            fitPorodBackground=True,
        )


def test_optimize_scaling_background_and_porod_rejects_zero_q():
    with pytest.raises(ValueError, match="finite, strictly positive Q"):
        optimizeScalingAndBackground(
            np.array([1.0, 2.0]),
            np.array([0.1, 0.1]),
            fitPorodBackground=True,
            measDataQ=np.array([0.0, 1.0]),
        )


def test_optimize_scaling_background_and_porod_uses_absolute_1d_q():
    optimizer = optimizeScalingAndBackground(
        np.array([1.0, 2.0]),
        np.array([0.1, 0.1]),
        fitPorodBackground=True,
        measDataQ=np.array([-0.5, 1.0]),
    )

    np.testing.assert_allclose(optimizer.qSupport, np.array([0.5, 1.0]))


def test_optimize_scaling_background_and_porod_rejects_non_finite_q():
    with pytest.raises(ValueError, match="finite, strictly positive Q"):
        optimizeScalingAndBackground(
            np.array([1.0, 2.0]),
            np.array([0.1, 0.1]),
            fitPorodBackground=True,
            measDataQ=np.array([0.5, np.inf]),
        )


def test_optimize_scaling_background_and_porod_scales_custom_coefficient_bound():
    q = np.array([0.5, 1.0])
    optimizer = optimizeScalingAndBackground(
        np.array([1.0, 2.0]),
        np.array([0.1, 0.1]),
        xBounds=[[0.0, 10.0], [-2.0, 2.0], [0.0, 1e-3]],
        fitPorodBackground=True,
        measDataQ=q,
    )

    assert optimizer._internal_bounds()[2] == [0.0, 1e-3 / q.min() ** 4]


def test_optimize_scaling_background_and_porod_uses_radial_2d_q():
    qx = np.array([3.0, 5.0])
    qy = np.array([4.0, 12.0])
    optimizer = optimizeScalingAndBackground(
        np.array([1.0, 2.0]),
        np.array([0.1, 0.1]),
        fitPorodBackground=True,
        measDataQ=[qx, qy],
    )

    np.testing.assert_allclose(optimizer.qSupport, np.array([5.0, 13.0]))
    np.testing.assert_allclose(optimizer._porodBasis, (5.0 / np.array([5.0, 13.0])) ** 4)


def test_mccore_routes_porod_fit_and_records_named_parameters():
    q = np.geomspace(0.05, 0.5, 40)
    model_intensity = np.exp(-3.0 * q)
    expected_parameters = np.array([1.8, 0.3, 2.5e-6])
    measured_intensity = fitted_intensity(model_intensity, expected_parameters, q)
    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": q,
                "I": measured_intensity,
                "ISigma": np.full_like(q, 0.01),
            }
        )
    )
    model = SimpleNamespace(
        func=SimpleNamespace(info=SimpleNamespace(parameters=SimpleNamespace(defaults={}))),
        kernel_static_parameters=lambda: {},
        make_kernel=lambda model_q: None,
        parameterSet=pandas.DataFrame([{"radius": 1.0}]),
        nContrib=1,
        volumes=None,
        calcModelIV=lambda parameters: (model_intensity, 1.0),
    )
    opt = McOpt(convCrit=0.0, maxIter=1, repetition=0, fitPorodBackground=True)

    core = McCore(analysis_bundle, model=model, opt=opt)

    np.testing.assert_allclose(core._opt.x0, expected_parameters, rtol=1e-6, atol=1e-12)
    assert core._opt.x0ParameterNames == list(POROD_FIT_PARAMETER_NAMES)


def test_mcopt_porod_state_round_trips_through_hdf(tmp_path):
    result_file = tmp_path / "porod-state.h5"
    path = ResultIndex(1).nxsEntryPoint / "optimization" / "repetition0"
    original = McOpt(
        accepted=3,
        gof=0.75,
        maxIter=100,
        maxAccept=10,
        modelI=np.array([1.0, 2.0]),
        repetition=0,
        step=8,
        x0=np.array([2.0, 0.5, 1.2e-6]),
        acceptedSteps=[0, 4, 8],
        acceptedGofs=[2.0, 1.0, 0.75],
        fitPorodBackground=True,
        x0ParameterNames=list(POROD_FIT_PARAMETER_NAMES),
    )
    original.store(result_file, path=path)

    loaded = McOpt(loadFromFile=result_file, loadFromRepetition=0)

    assert loaded.fitPorodBackground is True
    assert loaded.x0ParameterNames == list(POROD_FIT_PARAMETER_NAMES)
    np.testing.assert_allclose(loaded.x0, original.x0)


def test_mcopt_legacy_hdf_state_infers_disabled_porod_fit(tmp_path):
    result_file = tmp_path / "legacy-state.h5"
    path = ResultIndex(1).nxsEntryPoint / "optimization" / "repetition0"
    legacy_values = {
        "accepted": 1,
        "convCrit": 1.0,
        "gof": 0.75,
        "maxIter": 100,
        "maxAccept": 10,
        "modelI": np.array([1.0, 2.0]),
        "step": 8,
        "x0": np.array([2.0, 0.5]),
        "acceptedSteps": np.array([0, 8]),
        "acceptedGofs": np.array([2.0, 0.75]),
    }
    for key, value in legacy_values.items():
        storeKV(result_file, path / key, value)

    loaded = McOpt(loadFromFile=result_file, loadFromRepetition=0)

    assert loaded.fitPorodBackground is False
    assert loaded.x0ParameterNames == ["scale", "background"]


def test_mccore_optimize_returns_false_when_stop_requested():
    core = McCore.__new__(McCore)
    core._stopRequested = lambda: core._opt.step >= 3
    core._opt = SimpleNamespace(
        repetition=2,
        gof=10.0,
        accepted=0,
        step=0,
        maxAccept=100,
        maxIter=100,
        convCrit=0.0,
    )
    core.iterate = lambda: setattr(core._opt, "step", core._opt.step + 1)

    completed = core.optimize()

    assert completed is False
    assert core._opt.step == 3


def test_mccore_optimize_logs_progress_when_stopped(caplog):
    core = McCore.__new__(McCore)
    core._stopRequested = lambda: core._opt.step >= 1
    core._opt = SimpleNamespace(
        repetition=5,
        gof=10.0,
        accepted=0,
        step=0,
        maxAccept=100,
        maxIter=100,
        convCrit=0.0,
    )
    core.iterate = lambda: setattr(core._opt, "step", core._opt.step + 1)

    with caplog.at_level(logging.INFO, logger="mcsas3.mc_core"):
        completed = core.optimize()

    assert completed is False
    assert "Optimization of repetition 5 started." in caplog.text
    assert "Optimization of repetition 5 interrupted." in caplog.text


def test_mchat_request_stop_prevents_later_single_core_repetitions(monkeypatch, tmp_path):
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=3,
        nCores=1,
        maxIter=1,
    )
    started_repetitions = []

    monkeypatch.setattr(hat, "fillFitParameterLimits", lambda analysis_input: None)

    def fake_run_once(analysis_input, filename, repetition=0, bufferStdIO=False, resultIndex=1):
        started_repetitions.append(repetition)
        hat.request_stop()
        return None

    monkeypatch.setattr(hat, "runOnce", fake_run_once)

    hat.run(
        bundle_from_1d_dataframe(
            pandas.DataFrame(
                {
                    "Q": np.array([0.1, 1.0], dtype=float),
                    "I": np.array([1.0, 2.0], dtype=float),
                    "ISigma": np.array([0.1, 0.2], dtype=float),
                }
            )
        ),
        tmp_path / "unused.h5",
    )

    assert started_repetitions == [0]
    assert hat.lastRunStopped is True
    assert hat.isRunning is False


def test_mchat_run_once_buffers_logging_output(monkeypatch, tmp_path):
    hat = McHat(
        modelName="mcsas_sphere",
        fitParameterLimits={"radius": "auto"},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        nRep=1,
        nCores=1,
        maxIter=1,
    )
    hat._opt = SimpleNamespace(repetition=0, gof=1.5, accepted=2)
    hat._model = SimpleNamespace(
        resetParameterSet=lambda: None,
        kernel=SimpleNamespace(release=lambda: None),
    )

    class FakeMcCore:
        def __init__(self, analysis_input, model, opt, resultIndex, stop_requested):
            self._opt = opt

        def optimize(self):
            logging.getLogger("mcsas3.mc_core").info("buffered worker progress")
            return False

    monkeypatch.setattr("mcsas3.mc_hat.McCore", FakeMcCore)

    repetition, output, completed = hat.runOnce(
        bundle_from_1d_dataframe(
            pandas.DataFrame(
                {
                    "Q": np.array([0.1, 1.0], dtype=float),
                    "I": np.array([1.0, 2.0], dtype=float),
                    "ISigma": np.array([0.1, 0.2], dtype=float),
                }
            )
        ),
        tmp_path / "unused.h5",
        repetition=0,
        bufferStdIO=True,
    )

    assert repetition == 0
    assert completed is False
    assert "buffered worker progress" in output
    assert "Optimization of repetition 0 stopped before completion." in output


def test_mcanalysis_average_histogram_rejects_mismatched_bin_edges():
    analysis = McAnalysis.__new__(McAnalysis)
    analysis._repetitionList = [0, 1]
    analysis._concatHistograms = {0: {0: np.array([1.0]), 1: np.array([2.0])}}
    analysis._concatBinEdges = {0: {0: np.array([0.0, 1.0]), 1: np.array([0.0, 2.0])}}

    with pytest.raises(ValueError, match="identical histogram bin edges"):
        analysis.averageHistogram(0)


def test_mcanalysis_store_replaces_existing_histogram_group(tmp_path):
    result_file = tmp_path / "result.h5"
    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": np.array([0.1, 0.2, 0.3], dtype=float),
                "I": np.array([1.0, 1.2, 1.4], dtype=float),
                "ISigma": np.array([0.1, 0.1, 0.1], dtype=float),
            }
        )
    )
    model = McModel(
        modelName="mcsas_sphere",
        nContrib=2,
        fitParameterLimits={"radius": (1.0, 8.0)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        seed=123,
    )
    model.parameterSet.loc[:, "radius"] = [2.0, 4.0]
    model.volumes = np.array([1.0, 1.0], dtype=float)
    model.store(result_file, repetition=0)
    opt = McOpt(convCrit=0.0, maxIter=1, repetition=0)
    opt.x0 = np.array([1.0, 0.0], dtype=float)
    opt.gof = 1.0
    opt.accepted = 0
    opt.step = 0
    opt.modelI = np.ones(3, dtype=float)
    opt.acceptedSteps = [0]
    opt.acceptedGofs = [1.0]
    opt.store(result_file, path=ResultIndex(1).nxsEntryPoint / "optimization" / "repetition0")

    histogram_root = ResultIndex(1).nxsEntryPoint / "histograms"
    storeKV(result_file, histogram_root / "histRange0" / "average" / "yMean", np.array([99.0, 99.0]))
    storeKV(result_file, histogram_root / "histRange1" / "average" / "yMean", np.array([999.0]))

    hist_ranges = pandas.DataFrame(
        [
            dict(
                parameter="radius",
                nBin=2,
                binScale="linear",
                presetRangeMin=1.0,
                presetRangeMax=8.0,
                binWeighting="vol",
                autoRange=False,
            )
        ]
    )

    McAnalysis(result_file, analysis_bundle, hist_ranges, store=True)

    with h5py.File(result_file, "r") as h5f:
        stored_histograms = h5f[str(histogram_root)]
        assert list(stored_histograms.keys()) == ["histRange0"]
        y_mean = stored_histograms["histRange0"]["average"]["yMean"][()]

    assert y_mean.shape == (2,)
    assert not np.all(y_mean == 99.0)


def test_mcanalysis_reloads_and_reports_porod_enabled_fit(tmp_path):
    result_file = tmp_path / "porod-analysis.h5"
    q = np.geomspace(0.05, 0.5, 30)
    model = McModel(
        modelName="mcsas_sphere",
        nContrib=2,
        fitParameterLimits={"radius": (2.0, 2.5)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": 1.0, "sld_solvent": 0.0},
        seed=123,
    )
    model.parameterSet.loc[:, "radius"] = [2.0, 2.5]
    model.make_kernel([q])
    intensity_0, volume_0 = model.calcModelIV({"radius": 2.0})
    intensity_1, volume_1 = model.calcModelIV({"radius": 2.5})
    model_intensity = intensity_0 + intensity_1
    model.volumes = np.array([volume_0, volume_1])
    model.store(result_file, repetition=0)
    expected_parameters = np.array([1.7, 0.2, 3.5e-6])
    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": q,
                "I": fitted_intensity(model_intensity, expected_parameters, q),
                "ISigma": np.full_like(q, 0.01),
            }
        )
    )
    opt = McOpt(
        accepted=0,
        convCrit=0.0,
        gof=0.0,
        maxIter=1,
        maxAccept=1,
        modelI=model_intensity,
        repetition=0,
        step=0,
        x0=expected_parameters,
        acceptedSteps=[0],
        acceptedGofs=[0.0],
        fitPorodBackground=True,
        x0ParameterNames=list(POROD_FIT_PARAMETER_NAMES),
    )
    opt.store(result_file, path=ResultIndex(1).nxsEntryPoint / "optimization" / "repetition0")
    hist_ranges = pandas.DataFrame(
        [
            dict(
                parameter="radius",
                nBin=1,
                binScale="linear",
                presetRangeMin=1.0,
                presetRangeMax=3.0,
                binWeighting="vol",
                autoRange=False,
            )
        ]
    )

    analysis = McAnalysis(result_file, analysis_bundle, hist_ranges)

    assert analysis._concatOpts.loc[0, "porodCoefficient"] == pytest.approx(expected_parameters[2], rel=1e-6)
    np.testing.assert_allclose(
        analysis._concatI[0],
        fitted_intensity(model_intensity, expected_parameters, q),
        rtol=1e-6,
    )
    expected_background = background_intensity(expected_parameters, q)
    np.testing.assert_allclose(analysis._concatBackgroundI[0], expected_background, rtol=1e-6)
    np.testing.assert_allclose(analysis.modelIAvg.backgroundIMean, expected_background, rtol=1e-6)


def test_mcanalysis_run_report_uses_compact_porod_and_combined_progress_labels():
    analysis = McAnalysis.__new__(McAnalysis)
    analysis._repetitionList = [0, 1]
    analysis._optimizerInput = SimpleNamespace(q_support=np.array([0.1, 1.0]))
    analysis._optKeys = ["scaling", "background", "porodCoefficient", "gof", "accepted", "step"]
    analysis._averagedOpts = pandas.DataFrame(
        {
            "valMean": [2.0, 0.5, 1e-6, 1.25, 7.0, 100.0],
            "valStd": [0.1, 0.1, 1e-7, 0.25, 1.0, 10.0],
        },
        index=analysis._optKeys,
    )

    report = analysis.debugRunReport()

    assert "porod     :" in report
    assert "porodCoefficient" not in report
    assert "accepted  ≈  7.00e+00,   total  ≈  1.00e+02" in report
    assert "step      :" not in report


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


def test_sasmodels_sphere_unit_bridge_recovers_expected_volume_fraction(monkeypatch):
    sasmodels_cache = Path(".pytest_sasmodels_cache", "compiled_models")
    sasmodels_cache.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SAS_OPENCL", "none")
    monkeypatch.setenv("SAS_DLL_PATH", str(sasmodels_cache.resolve()))

    q_nm = np.geomspace(0.03, 0.3, 48)
    radius_nm = 35.0
    sld = 6.0
    sld_solvent = 1.0
    expected_volume_fraction = 0.037

    sas_model = sasmodels.core.load_model("sphere", dtype="default")
    sas_kernel = sas_model.make_kernel([q_nm / 10.0])
    _f, fsq, _r_eff, v_shell, _v_ratio = sasmodels.direct_model.call_Fq(
        sas_kernel,
        {"radius": radius_nm * 10.0, "sld": sld, "sld_solvent": sld_solvent},
    )
    reference_intensity = expected_volume_fraction * 100.0 * (fsq / v_shell)

    analysis_bundle = bundle_from_1d_dataframe(
        pandas.DataFrame(
            {
                "Q": q_nm,
                "I": reference_intensity,
                "ISigma": np.maximum(reference_intensity * 0.01, 1e-12),
            }
        )
    )

    model = McModel(
        modelName="sphere",
        modelDType="default",
        nContrib=1,
        fitParameterLimits={"radius": (radius_nm, radius_nm)},
        staticParameters={"background": 0.0, "scale": 1.0, "sld": sld, "sld_solvent": sld_solvent},
        seed=123,
    )
    model.parameterSet.loc[0, "radius"] = radius_nm
    model.make_kernel([q_nm])
    bridged_intensity, _volume = model.calcModelIV({"radius": radius_nm})

    expected_optimizer_scale = expected_volume_fraction / model.volume_fraction_correction_factor()
    np.testing.assert_allclose(reference_intensity, expected_optimizer_scale * bridged_intensity, rtol=1e-10)

    opt = McOpt(convCrit=0.0, maxIter=1, repetition=0)
    core = McCore(analysis_input=analysis_bundle, model=model, opt=opt)

    np.testing.assert_allclose(core._opt.x0[0], expected_optimizer_scale, rtol=5e-5)

    hist_ranges = pandas.DataFrame(
        [
            dict(
                parameter="radius",
                nBin=1,
                binScale="linear",
                presetRangeMin=radius_nm * 0.9,
                presetRangeMax=radius_nm * 1.1,
                binWeighting="vol",
                autoRange=False,
            )
        ]
    )
    with pytest.warns(RuntimeWarning):
        histogrammer = McModelHistogrammer(core, hist_ranges)

    np.testing.assert_allclose(histogrammer._histDict[0][0], expected_volume_fraction, rtol=5e-5)
    np.testing.assert_allclose(histogrammer._modes.loc[0, "totalValue"], expected_volume_fraction, rtol=5e-5)
