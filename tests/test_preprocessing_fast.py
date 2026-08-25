import numpy as np
import pandas
import pandas.testing as pdt
import pytest

from mcsas3.data_adapters import bundle_from_1d_dataframe, bundle_from_2d_arrays
from mcsas3.preprocessing import (
    prepare_1d_bundle,
    prepare_2d_bundle,
    rebin_1d_bundle,
    reconstruct_2d_from_clipped_bundle,
)


def test_prepare_1d_bundle_preserves_extra_compatibility_columns():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "I": np.array([5.0, 10.0, 20.0, 40.0, 50.0], dtype=float),
            "ISigma": np.array([0.5, 1.0, 2.0, 4.0, 5.0], dtype=float),
            "sample_id": np.array([10, 20, 30, 40, 50], dtype=int),
        }
    )
    raw_bundle = bundle_from_1d_dataframe(frame.loc[:, ["Q", "I", "ISigma"]])

    prepared = prepare_1d_bundle(
        raw_bundle,
        data_range=[1.0, 5.0],
        omit_q_ranges=[[1.5, 3.0]],
        nbins=0,
        source_frame=frame,
    )

    expected = frame.iloc[[1, 3]].reset_index(drop=True)
    pdt.assert_frame_equal(prepared.clipped.frame.reset_index(drop=True), expected)
    pdt.assert_frame_equal(prepared.binned.frame.reset_index(drop=True), expected)
    np.testing.assert_allclose(prepared.binned.bundle["Q"].signal, np.array([1.0, 4.0]))
    np.testing.assert_allclose(prepared.binned.bundle["signal"].signal, np.array([10.0, 40.0]))


def test_rebin_1d_bundle_returns_minimal_statistics_contract():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0, 2.0, 20.0], dtype=float),
            "I": np.array([10.0, 14.0, 100.0], dtype=float),
            "ISigma": np.array([1.0, 1.0, 2.0], dtype=float),
        }
    )
    clipped_bundle = bundle_from_1d_dataframe(frame)

    prepared = rebin_1d_bundle(clipped_bundle, nbins=2, iemin=0.1, source_frame=frame)

    assert len(prepared.frame) == 2
    assert list(prepared.frame.columns) == ["Q", "I", "ISigma", "QSigma"]

    first_bin = prepared.frame.iloc[0]
    second_bin = prepared.frame.iloc[1]

    np.testing.assert_allclose(first_bin["Q"], 1.5)
    np.testing.assert_allclose(first_bin["I"], 12.0)
    np.testing.assert_allclose(first_bin["ISigma"], 2.0)
    np.testing.assert_allclose(first_bin["QSigma"], 0.5)

    np.testing.assert_allclose(second_bin["Q"], 20.0)
    np.testing.assert_allclose(second_bin["I"], 100.0)
    np.testing.assert_allclose(second_bin["ISigma"], 10.0)
    np.testing.assert_allclose(second_bin["QSigma"], 0.2)

    np.testing.assert_allclose(prepared.bundle["Q"].signal, np.array([1.5, 20.0]))
    np.testing.assert_allclose(prepared.bundle["signal"].signal, np.array([12.0, 100.0]))


def test_rebin_1d_bundle_uses_absolute_intensity_for_uncertainty_floor():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0], dtype=float),
            "I": np.array([-5.0], dtype=float),
            "ISigma": np.array([0.0], dtype=float),
        }
    )
    clipped_bundle = bundle_from_1d_dataframe(frame)

    prepared = rebin_1d_bundle(clipped_bundle, nbins=1, iemin=0.1, source_frame=frame)

    np.testing.assert_allclose(prepared.frame.loc[0, "ISigma"], 0.5)


def test_prepare_1d_bundle_rejects_malformed_data_range():
    frame = pandas.DataFrame(
        data={
            "Q": np.array([1.0, 2.0], dtype=float),
            "I": np.array([10.0, 14.0], dtype=float),
            "ISigma": np.array([1.0, 1.0], dtype=float),
        }
    )
    raw_bundle = bundle_from_1d_dataframe(frame)

    with pytest.raises(ValueError, match="data_range must contain exactly two values"):
        prepare_1d_bundle(raw_bundle, data_range=[1.0], nbins=0)


def test_prepare_2d_bundle_rejects_negative_nbins():
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    raw_bundle = bundle_from_2d_arrays(intensity=intensity, intensity_sigma=sigma, qx=qx, qy=qy)

    with pytest.raises(ValueError, match="nbins must be zero or positive"):
        prepare_2d_bundle(
            raw_bundle,
            data_range=[0.0, 1.0],
            ortho_q0_range=[0.0, 1.0],
            ortho_q1_range=[0.0, 1.0],
            nbins=-1,
        )


def test_prepare_2d_bundle_clips_canonical_bundle_without_mcd_data():
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0
    raw_bundle = bundle_from_2d_arrays(intensity=intensity, intensity_sigma=sigma, qx=qx, qy=qy, mask=mask)

    prepared = prepare_2d_bundle(
        raw_bundle,
        data_range=[0.0, 1.0],
        ortho_q0_range=[0.0, 1.0],
        ortho_q1_range=[0.0, 1.0],
        nbins=0,
    )

    np.testing.assert_array_equal(prepared.clipped["signal"].signal, np.array([[5.0, 6.0], [9.0, 10.0]]))
    np.testing.assert_array_equal(prepared.clipped["Qx"].signal, np.array([[-0.5, 0.5], [-0.5, 0.5]]))
    np.testing.assert_array_equal(prepared.clipped["Qy"].signal, np.array([[-0.5, -0.5], [0.5, 0.5]]))
    assert prepared.binned is not prepared.clipped
    np.testing.assert_array_equal(prepared.binned["signal"].signal, prepared.clipped["signal"].signal)


def test_reconstruct_2d_from_clipped_bundle_restores_model_values_into_valid_pixels():
    coords = np.array([-1.5, -0.5, 0.5, 1.5], dtype=float)
    qx, qy = np.meshgrid(coords, coords)
    intensity = np.arange(16, dtype=float).reshape(4, 4)
    sigma = np.ones((4, 4), dtype=float)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1, 1] = True
    sigma[1, 2] = 0.0
    raw_bundle = bundle_from_2d_arrays(intensity=intensity, intensity_sigma=sigma, qx=qx, qy=qy, mask=mask)

    prepared = prepare_2d_bundle(
        raw_bundle,
        data_range=[0.0, 1.0],
        ortho_q0_range=[0.0, 1.0],
        ortho_q1_range=[0.0, 1.0],
        nbins=0,
    )

    reconstructed = reconstruct_2d_from_clipped_bundle(prepared.clipped, np.array([100.0, 200.0]))

    assert reconstructed.shape == (2, 2)
    assert np.isnan(reconstructed[0, 0])
    assert np.isnan(reconstructed[0, 1])
    np.testing.assert_allclose(reconstructed[1], np.array([100.0, 200.0]))
