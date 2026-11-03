"""
The grey reconstruction behind the h-max transform of the maxima detection (#46) is the one of scikit-image, in the
type of the seed.
"""
import numpy as np
import pytest
from skimage.morphology import reconstruction

from ClearMap.Analysis.Measurements import maxima_detection
import ClearMap.ImageProcessing.GreyReconstruction as grey_reconstruction  # grey_reconstruction upstream

PEAK, BUMP = (10, 10, 10), (10, 14, 10)  # A bump on the side of the peak, its own maximum without h_max


def _image(dtype):
    grid = np.indices((21, 25, 21)).astype(float)
    def blob(center, amplitude):
        return amplitude * np.exp(-sum((g - c) ** 2 for g, c in zip(grid, center)) / 2)
    return (100 + blob(PEAK, 1000) + blob(BUMP, 200)).astype(dtype)


@pytest.mark.parametrize('dtype', [np.uint16, np.float32])
def test_the_reconstruction_is_the_one_of_scikit_image(dtype):
    mask = _image(dtype)
    seed = (mask.astype(np.float32) - 5).clip(0).astype(dtype)

    reconstructed = grey_reconstruction.reconstruct(seed, mask)

    np.testing.assert_array_equal(reconstructed, reconstruction(seed, mask))
    assert reconstructed.dtype == seed.dtype


def test_label_representatives_gives_one_pixel_per_label():
    labels = np.zeros((6, 6, 4), dtype=int)
    labels[1:3, 1:3, 1:3] = 1  # a flat 2x2x2 maximum
    labels[4, 4, 2] = 2
    labels[0, 5, 0] = 5  # label numbers need not be consecutive
    points = np.vstack(maxima_detection.label_representatives(labels)).T
    assert len(points) == 3
    assert sorted(labels[tuple(points.T)].tolist()) == [1, 2, 5]


def test_label_representatives_keeps_background_on_request():
    labels = np.array([[0, 1], [1, 1]])
    without = np.vstack(maxima_detection.label_representatives(labels)).T
    with_background = np.vstack(maxima_detection.label_representatives(labels, eliminate_zero_label=False)).T
    assert labels[tuple(without.T)].tolist() == [1]
    assert sorted(labels[tuple(with_background.T)].tolist()) == [0, 1]


def test_label_representatives_without_labels_is_empty():
    points = np.vstack(maxima_detection.label_representatives(np.zeros((3, 3, 3), dtype=int))).T
    assert points.shape == (0, 3)
