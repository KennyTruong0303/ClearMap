import numpy as np

import ClearMap.Analysis.Measurements.maxima_detection as maxima_detection


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
