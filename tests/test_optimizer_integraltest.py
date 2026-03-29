# ruff: noqa: E402

import os
import shutil  # for file copy
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas
import pytest

SASMODELS_CACHE = Path(".pytest_sasmodels_cache", "compiled_models")
SASMODELS_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("SAS_OPENCL", "none")
os.environ.setdefault("SAS_DLL_PATH", str(SASMODELS_CACHE.resolve()))

from mcsas3 import mc_hat, mc_plot, workflows
from mcsas3.data_adapters import selected_bundle_from_processing
from mcsas3.mc_analysis import McAnalysis
from mcsas3.optimizer_input import optimizer_input_from_bundle

# Keep imports at module scope; moving them into helpers has triggered relative-import issues before.
warnings.filterwarnings("error")
pytestmark = pytest.mark.integration

FAST_N_CONTRIB = 96
FAST_MAX_ITER = 1500
FAST_N_REP = 1
FAST_SEED = 12345


def build_hat(
    *,
    model_name: str,
    fit_parameter_limits: dict,
    static_parameters: dict,
    conv_crit: float,
    result_index: int = 1,
    n_cores: int = 1,
    n_contrib: int = FAST_N_CONTRIB,
    max_iter: int = FAST_MAX_ITER,
    n_rep: int = FAST_N_REP,
    seed: int | None = FAST_SEED,
    **kwargs: dict,
) -> mc_hat.McHat:
    if n_cores > 1:
        os.environ["SAS_OPENCL"] = "none"

    return mc_hat.McHat(
        modelName=model_name,
        nContrib=n_contrib,
        modelDType="default",
        fitParameterLimits=fit_parameter_limits,
        staticParameters=static_parameters,
        maxIter=max_iter,
        convCrit=conv_crit,
        nRep=n_rep,
        nCores=n_cores,
        seed=seed,
        resultIndex=result_index,
        **kwargs,
    )


def build_simulation_inputs():
    measurement_data = workflows.prepare_1d_processing_data_from_file(
        filename=Path("testdata", "nPSize4.dat"),
        nbins=0,
        csvargs={
            "sep": ";",
            "header": None,
            "names": ["Q", "I", "ISigma"],
            "usecols": [0, 3, 4],
        },
        dataRange=[0.04, 1],
    )
    simulation_data = workflows.prepare_1d_processing_data_from_file(
        filename=Path("testdata", "fancyCubePD0p01.nxs"),
        pathDict={
            "Q": "/sasentry1/sasdata1/Q",
            "I": "/sasentry1/sasdata1/I",
            "ISigma": "/sasentry1/sasdata1/Idev",
        },
        dataRange=[0, 38],
    )
    return measurement_data, simulation_data


def factor_hist_ranges() -> pandas.DataFrame:
    return pandas.DataFrame(
        [
            dict(
                parameter="factor",
                nBin=50,
                binScale="log",
                presetRangeMin=0.1,
                presetRangeMax=3,
                binWeighting="vol",
                autoRange=True,
            ),
            dict(
                parameter="factor",
                nBin=50,
                binScale="linear",
                presetRangeMin=0.1,
                presetRangeMax=3,
                binWeighting="vol",
                autoRange=False,
            ),
        ]
    )


def run_simulation_fit(res_path: Path, *, n_cores: int, rebuild: bool = True) -> dict:
    measurement_processing, simulation_processing = build_simulation_inputs()
    simulation_input = optimizer_input_from_bundle(selected_bundle_from_processing(simulation_processing))

    if rebuild and res_path.is_file():
        res_path.unlink()

    if rebuild or not res_path.is_file():
        workflows.optimize_processing_data(
            measurement_processing,
            res_path,
            hat=build_hat(
                model_name="sim",
                fit_parameter_limits={"factor": (20, 40)},
                static_parameters={
                    "extrapY0": 2.21e-09,
                    "extrapScaling": 9.61e01,
                    "simDataQ0": simulation_input.q[0],
                    "simDataQ1": None,
                    "simDataI": simulation_input.i,
                    "simDataISigma": simulation_input.isigma,
                },
                conv_crit=14,
                n_cores=n_cores,
                n_rep=2 if n_cores > 1 else 1,
            ),
        )

    return measurement_processing


class testOptimizer(unittest.TestCase):
    def test_optimizer_2D_cylinder(self):
        resPath = Path("test_result2DCylinder.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_2d_processing_data_from_file(
            filename=Path("testdata", "009766_forSasView.h5"),
            dataRange=[0, np.inf],
            orthoQ0Range=[0, np.inf],
            orthoQ1Range=[0, np.inf],
            nbins=0,
        )

        mh = build_hat(
            model_name="cylinder",
            n_contrib=128,
            fit_parameter_limits={
                "radius": (5, 500),
                "length": (600, 1200),
                "phi": (90 - 90, 90 + 90),
            },
            static_parameters={
                "background": 0,
                "scale": 1,
                "sld": 6.3,  # e-6,
                "sld_solvent": 1,  # e-6, # D2O
                "theta": 90,
            },
            max_iter=500,
            conv_crit=1e5,
        )
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="length",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="phi",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_1D_mcsas_sphere_and_rehistogrammer(self):
        # uses an internal sphere function for the case the sasmodels don't want to work.
        # remove any prior results file:
        resPath = Path("test_resultssphere.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
            result_index=2,
        )

        # run the Monte Carlo method
        mh = build_hat(
            model_name="mcsas_sphere",
            fit_parameter_limits={"radius": (3.14, 314)},
            static_parameters={
                "background": 0,
                "scale": 1,
                "sld": 3.35e-5,
                "sld_solvent": 0,
            },
            result_index=2,
            conv_crit=1,
        )
        workflows.optimize_processing_data(analysis_input, resPath, result_index=2, hat=mh)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True, resultIndex=2)

        # -- -- --
        # def test_reHistogrammer(self):
        # immediately test the rehistogrammer as it requires the output of the steps until here..
        # read the configuration file
        # resPath = Path("test_resultssphere.h5")

        # clear prior results:
        del mh, histRanges

        # load the data

        analysis_input = workflows.load_result_processing_data(resPath, result_index=2)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="log",
                    presetRangeMin=5,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        # run the Monte Carlo method
        mcres = McAnalysis(resPath, analysis_input, histRanges, store=True, resultIndex=2)

        # plotting:
        # plot the histogram result
        mp = mc_plot.McPlot()
        # output file for plot:
        saveHistFile = resPath.with_suffix(".png")
        if saveHistFile.is_file():
            saveHistFile.unlink()
        mp.resultCard(mcres, saveHistFile=saveHistFile)

    def test_optimizer_1D_sphere_poor_inital_guess(self):
        # remove any prior results file:
        resPath = Path("S2870 BSA THF 1 1 d.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            filename=Path("testdata", "S2870 BSA THF 1 1 d.pdh"),
            nbins=100,
            csvargs={
                "sep": None,
                "header": None,
                "names": ["Q", "I", "ISigma"],
                "engine": "python",
                "skipinitialspace": True,
                "dtype": np.float32,
                "usecols": [0, 1, 2],
                "skip_blank_lines": True,
            },
        )

        # run the Monte Carlo method
        mh = build_hat(
            model_name="sphere",
            fit_parameter_limits={"radius": (3.14, 314)},
            static_parameters={"background": 0, "scale": 0.1e6, "sld": 33, "sld_solvent": 0},
            maxAccept=1e3,
            conv_crit=1,
        )
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_1D_sphere_with_hardspherestructure(self):
        # remove any prior results file:
        resPath = Path("test_resultshardsphere.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )

        # run the Monte Carlo method
        mh = build_hat(
            model_name="sphere@hardsphere",
            fit_parameter_limits={"radius": (3.14, 314)},
            static_parameters={
                "background": 0,
                "scale": 1,
                "radius_effective_mode": 1,  # effective radius follows radius
                "structure_factor_mode": 1,  # with beta approximation
                "volfraction": 0.01,
            },
            conv_crit=1,
        )
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)

        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=100,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_1D_sim0_singlecore(self):
        resPath = Path("test_resultssim_1D_singlecore.h5")
        analysis_input = run_simulation_fit(resPath, n_cores=1)
        histRanges = factor_hist_ranges()
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_1D_sim1_multicore(self):
        resPath = Path("test_resultssim_1D_multicore.h5")
        analysis_input = run_simulation_fit(resPath, n_cores=2)
        histRanges = factor_hist_ranges()
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_1D_sphere_state(self):
        # (re-)creates a state for the restore-state test.
        resPath = Path("test_state.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )

        # run the Monte Carlo method
        mh = build_hat(
            model_name="sphere",
            fit_parameter_limits={"radius": (1, 314)},
            static_parameters={"background": 0, "scale": 0.1e6},
            conv_crit=1,
        )
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)
        # state created

        del mh, analysis_input, histRanges

        analysis_input = workflows.load_result_processing_data(resPath)
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=10,
                    presetRangeMax=34,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=60,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=200,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    @pytest.mark.slow
    def test_optimizer_1D_sphere_accuratestate(self):
        # (re-)creates an accurate state for histogramming tests.
        resPath = Path("test_accuratestate.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            filename=Path("testdata", "quickstartdemo1.csv"),
            nbins=100,
            csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        )

        # run the Monte Carlo method
        mh = build_hat(
            model_name="sphere",
            n_contrib=300,
            fit_parameter_limits={"radius": (3.14, 314)},
            static_parameters={
                "background": 0,
                "scale": 1,
                "sld": 77.93,
                "sld_solvent": 9.45,
            },
            max_iter=100000,
            conv_crit=1,
            n_rep=50,
            n_cores=2,
            seed=None,
        )
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=3.14,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=3.142,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=25,
                    presetRangeMax=75,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=75,
                    presetRangeMax=150,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)
        # state created

        # def test_optimizer_1D_sphere_rehistogram_accuratestate(self):
        # for troubleshooting the histogramming function :
        del analysis_input, histRanges, mh

        analysis_input = workflows.load_result_processing_data(resPath)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=3.14,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=3.142,
                    presetRangeMax=25,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=25,
                    presetRangeMax=75,
                    binWeighting="vol",
                    autoRange=False,
                ),
                dict(
                    parameter="radius",
                    nBin=20,
                    binScale="linear",
                    presetRangeMin=75,
                    presetRangeMax=150,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        mcres = McAnalysis(resPath, analysis_input, histRanges, store=True)
        # test whether the volume fraction of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[1, "totalValue"]["valMean"], 0.027, atol=0.001)
        # test whether the volume fraction of the second population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[2, "totalValue"]["valMean"], 9.01e-02, atol=0.001)
        # test whether the volume fraction of the third population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[3, "totalValue"]["valMean"], 9.57e-02, atol=0.001)
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[1, "mean"]["valMean"], 1.11e01, atol=1)
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[2, "mean"]["valMean"], 4.71e01, atol=5)
        # test whether the mean dimension of the first population is within expectation:
        np.testing.assert_allclose(mcres._averagedModes.loc[3, "mean"]["valMean"], 1.03e02, atol=5)

    def test_optimizer_1D_gaussianchain(self):
        # remove any prior results file:
        resPath = Path("test_resultsgaussianchain.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            Path(r"testdata/S2870 BSA THF 1 1 d.pdh"),
            dataRange=[0.1, 4],
            nbins=50,
        )
        # run the Monte Carlo method
        mh = build_hat(
            model_name="mono_gauss_coil",
            fit_parameter_limits={"rg": (1, 20)},
            static_parameters={"background": 0, "i_zero": 0.00319},
            conv_crit=2,
        )
        # test step seems to be broken? Maybe same issue with multicore processing with sasview
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="rg",
                    nBin=25,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=30,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def broken_test_optimizer_1D_sphere_plus_fractal(self):
        """Thsi does not work as fractal model does not have a volume."""
        # remove any prior results file:
        resPath = Path("test_resultsplusporod.h5")
        if resPath.is_file():
            resPath.unlink()

        analysis_input = workflows.prepare_1d_processing_data_from_file(
            Path(r"testdata/S2870 BSA THF 1 1 d.pdh"),
            dataRange=[0.1, 4],
            nbins=50,
        )
        # run the Monte Carlo method
        mh = build_hat(
            model_name="sphere+fractal",
            fit_parameter_limits={"A_radius": (1, 20)},
            static_parameters={"background": 0, "i_zero": 0.00319},
            max_iter=1000,
            conv_crit=1,
        )
        # test step seems to be broken? Maybe same issue with multicore processing with sasview
        workflows.optimize_processing_data(analysis_input, resPath, hat=mh)
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="A_radius",
                    nBin=25,
                    binScale="linear",
                    presetRangeMin=0.1,
                    presetRangeMax=30,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(resPath, analysis_input, histRanges, store=True)

    def test_optimizer_nxsas_io(self):
        tpath = Path("testdata", "test_nexus_io.nxs")
        # tests whether I can read and write in the same nexus file
        if tpath.is_file():
            tpath.unlink()
        hpath = Path("testdata", "20190725_11_expanded_stacked_processed_190807_161306.nxs")

        shutil.copy(hpath, tpath)

        analysis_input = workflows.prepare_1d_processing_data_from_file(tpath)

        mh = build_hat(
            model_name="sphere",
            fit_parameter_limits={"radius": (0.2, 160)},
            static_parameters={"background": 0, "scale": 1e3},
            max_iter=500,
            conv_crit=4000,
        )

        workflows.optimize_processing_data(analysis_input, tpath, hat=mh)
        # histogram the determined size contributions
        histRanges = pandas.DataFrame(
            [
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="log",
                    presetRangeMin=1,
                    presetRangeMax=314,
                    binWeighting="vol",
                    autoRange=True,
                ),
                dict(
                    parameter="radius",
                    nBin=50,
                    binScale="linear",
                    presetRangeMin=1,
                    presetRangeMax=10,
                    binWeighting="vol",
                    autoRange=False,
                ),
            ]
        )
        _ = McAnalysis(tpath, analysis_input, histRanges, store=True)


if __name__ == "__main__":
    unittest.main()
