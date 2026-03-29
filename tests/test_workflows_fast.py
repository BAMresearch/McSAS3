from pathlib import Path

import h5py
import numpy as np
import pandas
import pytest

from mcsas3.data_adapters import STAGE_BINNED, STAGE_CLIPPED, STAGE_RAW, selected_bundle_from_processing
from mcsas3.workflows import (
    load_result_processing_data,
    optimize_processing_data,
    prepare_1d_processing_data,
    store_result_processing_data,
)


def _sample_frame() -> pandas.DataFrame:
    return pandas.DataFrame(
        data={
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
        }
    )


def test_prepare_1d_processing_data_builds_canonical_stages():
    processing = prepare_1d_processing_data(
        _sample_frame(),
        data_range=[1.0, 5.0],
        omit_q_ranges=[[1.5, 3.0]],
        nbins=0,
        analysis_stage=STAGE_CLIPPED,
    )

    assert set(processing.keys()) == {STAGE_RAW, STAGE_CLIPPED, STAGE_BINNED}
    assert getattr(processing, "analysis_stage") == STAGE_CLIPPED
    np.testing.assert_allclose(processing[STAGE_RAW]["Q"].signal, np.array([0.5, 1.0, 2.0, 4.0, 5.0]))
    np.testing.assert_allclose(selected_bundle_from_processing(processing)["Q"].signal, np.array([1.0, 4.0]))
    np.testing.assert_allclose(selected_bundle_from_processing(processing)["signal"].signal, np.array([10.0, 40.0]))


def test_store_and_load_result_processing_data_round_trip(tmp_path):
    result_file = tmp_path / "workflow_result.h5"
    processing = prepare_1d_processing_data(_sample_frame(), data_range=[1.0, 5.0], nbins=2)

    store_result_processing_data(
        result_file,
        processing,
        result_index=2,
        metadata={"filename": Path("input.dat"), "nbins": 2},
    )

    restored = load_result_processing_data(result_file, result_index=2)

    assert getattr(restored, "analysis_stage") == getattr(processing, "analysis_stage")
    np.testing.assert_allclose(restored[STAGE_RAW]["Q"].signal, processing[STAGE_RAW]["Q"].signal)
    np.testing.assert_allclose(restored[STAGE_BINNED]["signal"].signal, processing[STAGE_BINNED]["signal"].signal)
    with h5py.File(result_file, "r") as h5f:
        assert "/analyses/MCResult2/mcdata/filename" in h5f
        assert h5f["/analyses/MCResult2/mcdata/nbins"][()] == 2


def test_optimize_processing_data_runs_mchat_on_selected_bundle_and_stores_processing(tmp_path):
    class RecordingHat:
        def __init__(self) -> None:
            self.calls = []

        def run(self, analysis_data, filename, resultIndex=1) -> None:
            self.calls.append((analysis_data, Path(filename), resultIndex))

    processing = prepare_1d_processing_data(
        _sample_frame(),
        data_range=[1.0, 5.0],
        omit_q_ranges=[[1.5, 3.0]],
        analysis_stage=STAGE_CLIPPED,
    )
    result_file = tmp_path / "optimized_result.h5"
    hat = RecordingHat()

    returned = optimize_processing_data(
        processing,
        result_file,
        result_index=2,
        hat=hat,
        processing_metadata={"filename": Path("input.dat")},
    )

    assert returned is hat
    assert len(hat.calls) == 1
    analysis_data, filename, result_index = hat.calls[0]
    assert analysis_data is selected_bundle_from_processing(processing)
    assert filename == result_file
    assert result_index == 2

    restored = load_result_processing_data(result_file, result_index=2)
    np.testing.assert_allclose(restored[STAGE_CLIPPED]["Q"].signal, np.array([1.0, 4.0]))


def test_optimize_processing_data_rejects_hat_and_hat_kwargs_together(tmp_path):
    class RecordingHat:
        def run(self, analysis_data, filename, resultIndex=1) -> None:
            return None

    with pytest.raises(ValueError, match="either an McHat instance or McHat keyword arguments"):
        optimize_processing_data(
            prepare_1d_processing_data(_sample_frame(), nbins=0),
            tmp_path / "unused_result.h5",
            hat=RecordingHat(),
            nRep=1,
        )
