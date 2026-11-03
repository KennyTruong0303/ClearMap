"""
The maxima detection with an h-max transform (maxima_detection.h_max, #46): the grey reconstruction behind it is the
one of scikit-image, a bump lower than h_max on the side of a peak is not a maximum of its own, on the 16-bit images
of the microscope as on float ones, and every maximum found gets its center.
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


def _saddle_and_bump_height(image):
    """The lowest value between the peak and the bump, and how high the bump rises above it"""
    profile = image[10, PEAK[1]:BUMP[1] + 1, 10].astype(float)
    return profile.min(), profile[-1] - profile.min()


def _n_maxima(image, h_max):
    maxima = maxima_detection.find_maxima(image, h_max=h_max, shape=5, threshold=200)  # Not the flat background
    return len(maxima_detection.find_center_of_maxima(image, maxima=maxima))


@pytest.mark.parametrize('dtype', [np.uint16, np.float32])
def test_the_h_max_transform_lowers_the_peaks_by_h_max_and_flattens_a_lower_bump(dtype):
    image = _image(dtype)
    saddle, bump_height = _saddle_and_bump_height(image)

    lower = maxima_detection.h_max_transform(image, h_max=int(bump_height) + 2)
    assert lower[PEAK] == pytest.approx(float(image[PEAK]) - (int(bump_height) + 2))
    assert lower[BUMP] == pytest.approx(saddle)  # The bump is gone, down to the saddle
    assert maxima_detection.h_max_transform(image, h_max=10)[BUMP] == pytest.approx(float(image[BUMP]) - 10)


@pytest.mark.parametrize('dtype', [np.uint16, np.float32])
def test_a_bump_lower_than_h_max_is_not_a_maximum_of_its_own(dtype):
    image = _image(dtype)
    bump_height = _saddle_and_bump_height(image)[1]

    assert _n_maxima(image, None) == 2
    assert _n_maxima(image, h_max=int(bump_height) + 2) == 1
    assert _n_maxima(image, h_max=int(bump_height) // 2) == 2


def test_an_integer_h_max_on_a_16_bit_image_does_not_wrap_around():
    image = _image(np.uint16) - 100  # Background at 0, below h_max: source - h_max would wrap to ~65535

    assert maxima_detection.h_max_transform(image, 5).max() == pytest.approx(image.max() - 5)


@pytest.mark.parametrize('dtype', [np.uint16, np.float32])
def test_the_reconstruction_is_the_one_of_scikit_image(dtype):
    mask = _image(dtype)
    seed = (mask.astype(np.float32) - 5).clip(0).astype(dtype)

    reconstructed = grey_reconstruction.reconstruct(seed, mask)

    np.testing.assert_array_equal(reconstructed, reconstruction(seed, mask))
    assert reconstructed.dtype == seed.dtype


def test_every_maximum_gets_its_center():
    maxima = np.zeros((10, 10, 10), dtype=bool)
    maxima[2, 2, 2] = maxima[7, 7, 7] = True

    centers = maxima_detection.find_center_of_maxima(maxima.astype(float), maxima=maxima)

    np.testing.assert_array_equal(centers, [[2, 2, 2], [7, 7, 7]])


def test_a_maximum_touching_itself_only_diagonally_gets_one_center():
    maxima = np.zeros((10, 10, 10), dtype=bool)
    maxima[4, 4, 4] = maxima[5, 5, 4] = maxima[5, 5, 5] = True  # one flattened top, joined only at corners

    centers = maxima_detection.find_center_of_maxima(maxima.astype(float), maxima=maxima)

    np.testing.assert_allclose(centers, [[14 / 3, 14 / 3, 13 / 3]])


def test_a_flattened_peak_with_diagonal_steps_gives_one_center_with_h_max():
    # A ridge one pixel wide that steps diagonally: h_max flattens it into one
    # plateau whose pixels touch only at their edges.
    image = np.zeros((12, 12, 3))
    for i in range(2, 9):
        image[i, i, 1] = 500
    image[5, 5, 1] = 510
    maxima = maxima_detection.find_maxima(image, h_max=20, shape=3, threshold=100)

    assert len(maxima_detection.find_center_of_maxima(image, maxima=maxima)) == 1


def _dim_cell_beside_a_brighter_slope():
    """A dim cell (peak 250) whose window holds a brighter cell's slope (240) but not its peak"""
    grid = np.indices((31, 9, 9)).astype(float)
    def blob(center, amplitude, sigma):
        return amplitude * np.exp(-sum((g - c) ** 2 for g, c in zip(grid, center)) / (2 * sigma ** 2))
    return blob((4, 4, 4), 739, 2) + blob((12, 4, 4), 250, 1.5)


def test_h_max_keeps_a_dim_cell_whose_window_holds_a_brighter_slope():
    image = _dim_cell_beside_a_brighter_slope()
    assert 235 < image[7, 4, 4] < 245  # The bright slope, in the dim cell's window, under the dim peak

    without = maxima_detection.find_maxima(image, h_max=None, shape=11, threshold=100)
    with_h_max = maxima_detection.find_maxima(image, h_max=20, shape=11, threshold=100)

    # h_max lowers the dim peak to about 230, under the slope; it must still be a maximum
    assert without[12, 4, 4] and without[4, 4, 4]
    assert with_h_max[12, 4, 4] and with_h_max[4, 4, 4]


def test_h_max_window_still_keeps_only_the_higher_of_two_close_peaks():
    grid = np.indices((21, 9, 9)).astype(float)
    image = sum(a * np.exp(-sum((g - c) ** 2 for g, c in zip(grid, center)) / 2)
                for center, a in [((7, 4, 4), 1000), ((11, 4, 4), 600)])  # Both well above h_max, 4 apart

    maxima = maxima_detection.find_maxima(image, h_max=20, shape=11, threshold=100)

    assert maxima[7, 4, 4] and not maxima[11, 4, 4]
    assert maxima_detection.find_maxima(image, h_max=20, shape=5, threshold=100)[11, 4, 4]


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
