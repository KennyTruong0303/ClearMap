import numpy as np
from scipy import ndimage

import ClearMap.Analysis.Measurements.shape_detection as shape_detection


def blurred_ball(shape, center, radius, amplitude, sigma=1.):
    grid = np.indices(shape)
    ball = sum((g - c) ** 2 for g, c in zip(grid, center)) <= radius ** 2
    return amplitude * ndimage.gaussian_filter(ball.astype(float), sigma), ball


def test_cut_relative_keeps_pixels_above_fraction_of_own_value():
    image = np.array([0, 2, 4, 8, 4, 2, 0, 1, 3, 6, 3, 1], dtype=float)[:, None, None]
    label = np.array([0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])[:, None, None]
    seeds = np.array([[3, 0, 0], [9, 0, 0]])
    cut = shape_detection.cut_relative(label, seeds, image, .5)
    assert cut.ravel().tolist() == [0, 0, 1, 1, 1, 0, 0, 0, 2, 2, 2, 0]


def test_cut_relative_drops_parts_not_connected_to_seed():
    image = np.zeros((9, 1, 1))
    image[2] = image[6] = 10
    label = np.ones((9, 1, 1), dtype=int)
    cut = shape_detection.cut_relative(label, np.array([[2, 0, 0]]), image, .5)
    assert np.flatnonzero(cut).tolist() == [2]


def test_cut_relative_removes_labels_without_seed():
    image = np.full((4, 1, 1), 10.)
    label = np.array([1, 1, 3, 3])[:, None, None]
    cut = shape_detection.cut_relative(label, np.array([[0, 0, 0], [3, 0, 0]]), image, .5)
    assert cut.ravel().tolist() == [1, 1, 0, 0]


def test_cut_relative_truncates_fractional_seeds_like_the_markers():
    image = np.array([0, 2, 4, 8, 4, 2, 0], dtype=float)[:, None, None]
    label = np.ones((7, 1, 1), dtype=int)
    exact = shape_detection.cut_relative(label, np.array([[3, 0, 0]]), image, .5)
    fractional = shape_detection.cut_relative(label, np.array([[3.7, 0, 0]]), image, .5)
    assert np.array_equal(exact, fractional)


def test_cut_relative_without_seeds_returns_empty_label():
    cut = shape_detection.cut_relative(np.ones((3, 3, 1), dtype=int), np.zeros((0, 3)), np.ones((3, 3, 1)), .5)
    assert not cut.any()


def test_cut_relative_smoothed_reference_ignores_a_single_bright_pixel():
    image = np.zeros((15, 1, 1))
    image[4:11] = 10
    image[7] = 30  # one bright pixel inside a uniform object
    label = (image > 0).astype(int)
    seeds = np.array([[7, 0, 0]])
    unsmoothed = shape_detection.cut_relative(label, seeds, image, .5)
    smoothed = shape_detection.cut_relative(label, seeds, image, .5, sigma=(1, 0, 0))
    assert (unsmoothed > 0).sum() == 1
    assert (smoothed > 0).sum() == 7


def test_detect_shape_relative_cut_makes_size_independent_of_brightness():
    dim, _ = blurred_ball((24, 24, 24), (12, 12, 12), 5, 100)
    bright, _ = blurred_ball((24, 24, 24), (12, 12, 12), 5, 1000)
    # Blurring moves a small ball's half-maximum contour slightly inside its
    # edge, so the exact target of a 0.5 cut is the half-maximum region.
    half_maximum = dim >= .5 * dim.max()
    seeds = np.array([[12, 12, 12]])
    sizes = {}
    for name, image in [('dim', dim), ('bright', bright)]:
        absolute = shape_detection.detect_shape(image, seeds, threshold=40)
        relative = shape_detection.detect_shape(image, seeds, threshold=1, relative_cut=.5)
        sizes[name] = (int((absolute == 1).sum()), int((relative == 1).sum()))
    # An absolute threshold makes the bright object larger; the relative cut does not.
    assert sizes['bright'][0] > 1.5 * sizes['dim'][0]
    assert sizes['bright'][1] == sizes['dim'][1] == half_maximum.sum()


def test_detect_shape_relative_cut_trims_the_reference_image():
    image, _ = blurred_ball((24, 24, 24), (12, 12, 12), 5, 500)
    flat = np.ones_like(image)  # watershed on a flat source fills the whole mask
    seeds = np.array([[12, 12, 12]])
    shapes = shape_detection.detect_shape(flat, seeds, threshold=0, relative_cut=.5, reference=image)
    assert np.array_equal(shapes == 1, image >= .5 * image.max())


def test_detect_shape_adjacent_seeds_keep_their_own_labels():
    # Seeds as radius-1 spheres weighted by ID summed 1 + 2 into a false label 3.
    image = np.ones((6, 6, 3))
    seeds = np.array([[2, 2, 1], [2, 3, 1]])
    shapes = shape_detection.detect_shape(image, seeds, threshold=0)
    assert set(np.unique(shapes)) == {1, 2}
    assert shapes[2, 2, 1] == 1 and shapes[2, 3, 1] == 2


def test_detect_shape_close_seeds_do_not_take_another_seeds_label():
    # Seeds 1 and 2 two pixels apart used to write 1 + 2 = 3 between them,
    # colliding with the real seed 3.
    image = np.ones((9, 9, 3))
    seeds = np.array([[2, 2, 1], [2, 4, 1], [6, 6, 1]])
    peaks = shape_detection.labeled_pixels_from_centers(seeds, np.arange(1, 4), image.shape)
    assert np.flatnonzero(peaks).size == 3
    assert [peaks[tuple(p)] for p in seeds] == [1, 2, 3]


def test_detect_shape_accepts_fractional_seeds():
    image, _ = blurred_ball((24, 24, 24), (12, 12, 12), 5, 500)
    exact = shape_detection.detect_shape(image, np.array([[12, 12, 12]]), threshold=50, relative_cut=.5)
    fractional = shape_detection.detect_shape(image, np.array([[12.6, 12.4, 12.9]]), threshold=50, relative_cut=.5)
    assert np.array_equal(exact, fractional)


def test_labeled_pixels_from_centers_works_in_two_dimensions():
    peaks = shape_detection.labeled_pixels_from_centers(np.array([[1, 2], [3, 0]]), np.array([5, 7]), (4, 4))
    assert peaks[1, 2] == 5 and peaks[3, 0] == 7 and np.count_nonzero(peaks) == 2


def test_detect_shape_unchanged_without_relative_cut():
    image, _ = blurred_ball((24, 24, 24), (12, 12, 12), 5, 500)
    seeds = np.array([[12, 12, 12], [5, 5, 5]])
    default = shape_detection.detect_shape(image, seeds, threshold=50)
    explicit = shape_detection.detect_shape(image, seeds, threshold=50, relative_cut=None,
                                            reference=np.zeros_like(image))
    assert np.array_equal(default, explicit)
