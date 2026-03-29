import importlib.util
from pathlib import Path

import numpy as np
import pandas

import mcsas3


def test_public_api_exports_canonical_workflow_entrypoints():
    assert mcsas3.DEFAULT_ANALYSIS_STAGE == mcsas3.STAGE_BINNED
    assert mcsas3.ProcessingData is not None
    assert mcsas3.DataBundle is not None
    assert mcsas3.BaseData is not None
    assert callable(mcsas3.prepare_1d_processing_data)
    assert callable(mcsas3.prepare_1d_processing_data_from_file)
    assert callable(mcsas3.prepare_2d_processing_data)
    assert callable(mcsas3.prepare_2d_processing_data_from_file)
    assert callable(mcsas3.optimize_processing_data)
    assert callable(mcsas3.load_result_processing_data)
    assert callable(mcsas3.analysis_data_from_bundle)
    assert callable(mcsas3.selected_bundle_from_processing)


def test_public_api_prepare_1d_processing_data_from_dataframe():
    frame = pandas.DataFrame(
        {
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
        }
    )

    processing = mcsas3.prepare_1d_processing_data(
        frame,
        data_range=[1.0, 5.0],
        omit_q_ranges=[[1.5, 3.0]],
        nbins=0,
        analysis_stage=mcsas3.STAGE_CLIPPED,
    )

    assert isinstance(processing, mcsas3.ProcessingData)
    assert getattr(processing, "analysis_stage") == mcsas3.STAGE_CLIPPED
    np.testing.assert_allclose(mcsas3.selected_bundle_from_processing(processing)["Q"].signal, np.array([1.0, 4.0]))


def test_public_api_prepare_1d_processing_data_from_file(tmp_path):
    filename = tmp_path / "input.csv"
    filename.write_text("0.1;1.0;0.1\n0.2;2.0;0.2\n")

    processing = mcsas3.prepare_1d_processing_data_from_file(
        filename,
        csvargs={"sep": ";", "header": None, "names": ["Q", "I", "ISigma"]},
        QUnits="1 / angstrom",
        IUnits="1 / centimeter / steradian",
        nbins=0,
    )

    selected = mcsas3.selected_bundle_from_processing(processing)
    analysis_data = mcsas3.analysis_data_from_bundle(selected)

    np.testing.assert_allclose(selected["Q"].signal, np.array([1.0, 2.0]))
    np.testing.assert_allclose(selected["signal"].signal, np.array([100.0, 200.0]))
    np.testing.assert_allclose(analysis_data["Q"][0], np.array([1.0, 2.0]))
    np.testing.assert_allclose(analysis_data["I"], np.array([100.0, 200.0]))


def test_public_api_result_processing_round_trip(tmp_path):
    result_file = tmp_path / "result.h5"
    processing = mcsas3.prepare_1d_processing_data(
        pandas.DataFrame(
            {
                "Q": np.array([1.0, 2.0], dtype=float),
                "I": np.array([10.0, 20.0], dtype=float),
                "ISigma": np.array([1.0, 2.0], dtype=float),
            }
        ),
        nbins=0,
    )

    mcsas3.store_result_processing_data(result_file, processing, metadata={"filename": Path("input.dat")})
    restored = mcsas3.load_result_processing_data(result_file)

    np.testing.assert_allclose(restored[mcsas3.STAGE_RAW]["Q"].signal, np.array([1.0, 2.0]))


def test_quickstart_notebook_uses_canonical_workflow_api():
    notebook_text = Path("notebooks/McSAS3.ipynb").read_text()

    assert "prepare_1d_processing_data_from_file" in notebook_text
    assert "optimize_processing_data" in notebook_text
    assert "McAnalysis(resPath, processing" in notebook_text
    assert "McData1D" not in notebook_text
    assert "measDataLink" not in notebook_text


def test_legacy_mcdata_modules_are_removed():
    assert importlib.util.find_spec("mcsas3.mc_data") is None
    assert importlib.util.find_spec("mcsas3.mc_data_1d") is None
    assert importlib.util.find_spec("mcsas3.mc_data_2d") is None
