# -*- coding: utf-8 -*-
"""
MaximaDetection
===============

Collection of routines to detect maxima in scalar images.

Used for finding cells or intensity peaks.
"""
__author__ = 'Christoph Kirst <christoph.kirst.ck@gmail.com>'
__license__ = 'GPLv3 - GNU General Pulic License v3 (see LICENSE)'
__copyright__ = 'Copyright © 2020 by Christoph Kirst'
__webpage__ = 'https://idisco.info'
__download__ = 'https://www.github.com/ChristophKirst/ClearMap2'

from typing import Tuple

import numpy as np

import scipy.ndimage.measurements as ndm
import scipy.ndimage.filters as ndf

import skimage.morphology

import ClearMap.ImageProcessing.GreyReconstruction as gr

import ClearMap.Utils.Timer as tmr
import ClearMap.Utils.HierarchicalDict as hdict


##############################################################################
# Basic Transforms
##############################################################################
   
def h_max_transform(source, h_max):
    """
    H-maximum transform of an array.

    Arguments
    ---------
    source : array
        Input image.
    h_max : float or None
        H parameter of h-max transform, if None return source.

    Returns
    -------
    transformed : array
        H-max transformed image if h is not None (as float32 for an integer image).
    """
    if h_max is None:
        return source
    # In an unsigned type, source - h_max wraps around below h_max: work in float (exact for 8 and 16-bit images)
    values = source if np.issubdtype(source.dtype, np.floating) else source.astype(np.float32)
    return gr.reconstruct(values - h_max, values)


def local_max(source, shape=5):
    """
    Calculates local maxima of an image

    Arguments
    ---------
    source : array
        Input image.
    shape : int, tuple or None
        Shape of the volume to search for maxima.

    Returns
    -------
    local_max : array
        Mask that is True at local maxima.
    """

    if shape is None:
        return source

    if not isinstance(shape, tuple):
        shape = (shape,) * source.ndim

    return ndf.maximum_filter(source, size=shape) == source


def local_max_of_peaks(source, shape=5):
    """
    Calculates the local maxima among the peaks of an image

    A peak is a regional maximum: a plateau that no higher pixel touches. A
    pixel is kept if it lies on a peak and no other peak within the window is
    higher. Unlike :func:`local_max`, a peak is compared with other peaks only,
    not with the slopes of brighter neighbours.

    Arguments
    ---------
    source : array
        Input image, e.g. an h-max transformed image.
    shape : int, tuple or None
        Shape of the volume to search for maxima. If None, keep all peaks.

    Returns
    -------
    local_max : array
        Mask that is True at the local maxima among the peaks.
    """
    peaks = skimage.morphology.local_maxima(source, connectivity=source.ndim, allow_borders=True).astype(bool)

    if shape is None:
        return peaks

    if not isinstance(shape, tuple):
        shape = (shape,) * source.ndim

    tops = np.where(peaks, source, -np.inf)
    return peaks & (ndf.maximum_filter(tops, size=shape) == tops)


def extended_max(source, h_max=0):
    """
    Calculates extended h-maxima of an image

    Arguments
    ---------
    source : array
        Input image.
    h_max : float or None
        H parameter of h-max transform. If None, calculate local maxima only.

    Returns
    -------
    maxima : array
        Extended maxima of the image.

    Note
    ----
    Extended maxima are the local maxima of the h-max transform.
    """
    # h max transform
    if h_max is not None and h_max > 0:
        source = h_max_transform(source, h_max)

    # max
    return local_max(source)


##############################################################################
# Maxima Detection 
##############################################################################


def find_maxima(source, h_max=None, shape=5, threshold=None, verbose=None):
    """
    Find local and extended maxima in an image.

    Arguments
    ---------
    source : array
        The source data.
    h_max : float or None
        H parameter for the initial h-Max transform.
        If None, do not perform a h-max transform.
    shape : int or tuple
        Shape for the structure element for the local maxima filter.
    threshold : float or None
        If float, include only maxima larger than this threshold.
    verbose : bool
        Print progress info.

    Returns
    -------
    maxima : array
        Binary image with True pixel at extended maxima.

    Notes
    -----
    This routine performs a h-max transform, followed by a local maxima search
    and thresholding of the maxima. With h_max, the local maxima are searched
    among the peaks of the transform only (:func:`local_max_of_peaks`).

    See also
    --------
    :func:`h_max_transform`, :func:`local_max`, :func:`local_max_of_peaks`
    """
    if verbose:
        timer = tmr.Timer()
        hdict.pprint(head='Find Maxima:', h_max=h_max, shape=shape, threshold=threshold)

    # extended maxima
    maxima = h_max_transform(source, h_max=h_max)

    # local maxima
    if h_max:
        # The h-max transform lowers each peak by h_max but leaves the slopes around it: in a window, a dim
        # peak lowered under a brighter neighbour's slope was lost. Compare the peaks with each other only.
        maxima = local_max_of_peaks(maxima, shape=shape)
    else:
        maxima = local_max(maxima, shape=shape)

    # thresholding
    if threshold is not None:
        maxima = np.logical_and(maxima, source >= threshold)

    if verbose:
        timer.print_elapsed_time(head='Find Maxima')

    return maxima


def find_center_of_maxima(source, maxima=None, label=None, verbose=False):
    """
    Find center of detected maxima weighted by intensity

    Arguments
    ---------
    source : array
        Intensity image data.
    maxima : array or None
        Binary array indicating the maxima. If label is not None this can be None.
    label : array or None
        Labeled image of the shapes of the maxima.
        If None, determined from maxima, joining pixels that touch at faces,
        edges or corners, so a flattened maximum gets one center.
    verbose : bool
        Print progress info.

    Returns
    -------
    coordinates : array
        Coordinates of the n centers of maxima as (n,d)-array.
    """
    if verbose:
        timer = tmr.Timer()
        print('Center of Maxima initialized!')

    # center of maxima
    if label is None:
        # Full connectivity, as for the maxima without h_max in Cells.detect_cells_block:
        # with face connectivity only, a flattened maximum touching itself diagonally got several centers
        label, n_label = ndm.label(maxima, structure=np.ones((3,) * np.ndim(maxima), dtype=bool))
    else:
        n_label = label.max()

    if n_label > 0:
        centers = np.array(ndm.center_of_mass(source, label, index=np.arange(1, n_label + 1)))  # Labels 1 to n
    else:
        centers = np.zeros((0, source.ndim))

    if verbose:
        timer.print_elapsed_time(f'Center of Maxima: {centers.shape[0]} maxima detected')

    return centers

def label_representatives(A:np.ndarray,eliminate_zero_label=True)->Tuple[np.ndarray,...]:
    """Return the multi-index of one element per non empty labeled region.
        The 0 labeled region is ignored by default and can be included optionally.

    Parameters
    ----------
    A : np.ndarray
        The labeled regions
    eliminate_zero_label : bool, optional
        If the representative for the 0 label is to be eliminated, 
        by default True

    Returns
    -------
    tuple[np.ndarray,...]
        The multi indices of one representative point per region, the ith 
        coordinate of the kth point is the kth entry of the ith array in 
        the tuple.
    """
    labels,indices = np.unique(A,return_index=True)
    if eliminate_zero_label:
        indices = indices[np.where(labels)]
    multi_indices = np.unravel_index(indices,A.shape)
    return multi_indices
