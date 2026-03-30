import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas
import pytest
import sasmodels.core
import sasmodels.direct_model

from mcsas3.data_adapters import bundle_from_1d_dataframe
from mcsas3.mc_analysis import McAnalysis
from mcsas3.mc_core import McCore
from mcsas3.mc_hat import McHat
from mcsas3.mc_model import McModel
from mcsas3.mc_model_histogrammer import McModelHistogrammer
from mcsas3.mc_opt import McOpt
from mcsas3.osb import optimizeScalingAndBackground


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
    from mcsas3.mc_model import McSimPseudoModel

    with pytest.raises(ValueError, match="Missing: simDataQ1, simDataI, simDataISigma"):
        McSimPseudoModel(simDataQ0=np.array([0.1, 0.2], dtype=float))


def test_mcopt_instances_do_not_share_accepted_history():
    first = McOpt()
    second = McOpt()

    first.acceptedSteps.append(5)
    first.acceptedGofs.append(0.25)

    assert second.acceptedSteps == []
    assert second.acceptedGofs == []


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
    model.kernel = model.func.make_kernel([q_nm])
    bridged_intensity, _volume = model.calcModelIV({"radius": radius_nm})

    expected_optimizer_scale = expected_volume_fraction / McModelHistogrammer._correctionFactor
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
