# -*- coding: utf-8 -*-
"""
ShapeDetection
==============

Module with routines for shape and size detection of objects such as cells.

Note
----
The shape detection is based on a seeded and masked watershed. The module is 
based on the ndimage library. For faster implementation of intensity 
and radial measurements see the modules listed below.

See also
--------
:mod:`ClearMap.Analysis.Measurements.MeasureExpression` and 
:mod:`ClearMap.Analysis.Measurements.MeasureRadius` 
"""
__author__ = 'Christoph Kirst <christoph.kirst.ck@gmail.com>'
__license__ = 'GPLv3 - GNU General Pulic License v3 (see LICENSE.txt)'
__copyright__ = 'Copyright © 2020 by Christoph Kirst'
__webpage__ = 'https://idisco.info'
__download__ = 'https://www.github.com/ChristophKirst/ClearMap2'


import numpy as np

import skimage.morphology
import scipy.ndimage
import scipy.ndimage.measurements

import ClearMap.IO.IO as io

import ClearMap.Analysis.Measurements.Voxelization as vox

import ClearMap.Utils.Timer as tmr
import ClearMap.Utils.HierarchicalDict as hdict


##############################################################################
# Cell shape detection
##############################################################################


def labeled_pixels_from_centers(centers,weights,shape):
    """label the pixels specify by the centers with the weights.

    Parameters
    ----------
    centers : np.ndarray
        (n_points,dim) array with points coords, its dtype is the one of weights
    weights : np.ndarray
        (n_points,) shaped array
    shape : tuple
        the shape of the output array.
    """

    if centers.shape[0]!=weights.shape[0]:
        raise ValueError("The number of weights must equal the number of points.")
    
    if len(shape)!=centers.shape[1]:
        raise ValueError("Received shape, points with points.shape[1] != len(shape) ")
    
    B = np.zeros(shape,dtype = weights.dtype)
    B[tuple(np.asarray(centers).T)]=weights
    return B


def seed_pixels(seeds):
    """
    Integer pixel coordinates of seeds.

    Fractional coordinates, such as h_max centres of mass, are truncated, as the
    voxelizer previously used for the seeds did.

    Arguments
    ---------
    seeds : array
        Seed coordinates, one row per seed.

    Returns
    -------
    pixels : array
        Integer seed coordinates.
    """
    points = np.asarray(seeds)
    if not np.issubdtype(points.dtype, np.integer):
        points = np.trunc(points).astype(int)
    return points


def detect_shape(source, seeds, threshold=None, verbose=False, processes=None,
                 relative_cut=None, relative_cut_sigma=None, reference=None):
    """
    Detect object shapes by generating a labeled image from seeds.
  
    Arguments
    ---------
    source : array, str or Source
        Source image.
    seeds : array, str or Source
        Cell centers as point coordinates.
    threshold : float or None
        Threshold to determine mask for watershed, pixel below this are
        treated as background. If None, the seeds are expanded indefinitely.
    verbose :bool
        If True, print progress info.
    relative_cut : float or None
        If not None, trim each object to the pixels at or above this fraction
        of its own reference value (see :func:`cut_relative`), so its size no
        longer grows with its brightness. Use a low threshold with it, so the
        watershed does not cut objects short first.
    relative_cut_sigma : float, tuple or None
        Gaussian sigma in pixels to smooth the image the reference value is
        read from. Use about half the point spread width.
    reference : array, str, Source or None
        Image to cut, e.g. the background corrected image. If None, use source.
  
    Returns
    -------
    shapes : array
        Labeled image, where each label indicates an object.
    """

    if verbose:
        timer = tmr.Timer()
        hdict.pprint(head='Shape detection', threshold=threshold,
                     relative_cut=relative_cut, relative_cut_sigma=relative_cut_sigma)
  
    source = io.as_source(source).array
    seeds = io.as_source(seeds)

    mask = None if threshold is None else source > threshold

    points = seed_pixels(seeds.array)
    peaks = labeled_pixels_from_centers(points,np.arange(1, points.shape[0]+1), source.shape)
    try:
        shapes = skimage.morphology.watershed(-source, peaks, mask=mask)
    except AttributeError:
        shapes = skimage.segmentation.watershed(-source, peaks, mask=mask)
    # shapes = watershed_ift(-source.astype('uint16'), peaks)
    # shapes[numpy.logical_not(mask)] = 0

    if relative_cut is not None:
        reference = source if reference is None else io.as_source(reference).array
        shapes = cut_relative(shapes, points, reference, relative_cut, sigma=relative_cut_sigma)

    if verbose:
        timer.print_elapsed_time('Shape detection')

    return shapes


def cut_relative(label, seeds, image, fraction, sigma=None):
    """
    Trim each labeled object to the pixels at or above a fraction of its own value.

    Object i + 1 belongs to seed i, as in :func:`detect_shape`. Its reference
    value is the image at the seed, smoothed by sigma if given; pixels of the
    object below fraction times that value are removed, as is any part no longer
    connected to the seed. For a blurred object of uniform intensity the edge
    lies at half the interior intensity, so fraction 0.5 recovers its outline
    at any brightness. Labels without a seed are removed.

    Arguments
    ---------
    label : array
        Labeled image, e.g. the result of the watershed in :func:`detect_shape`.
    seeds : array
        Seed coordinates, one row per object, in label order.
    image : array
        Image to cut, e.g. the background corrected image.
    fraction : float
        Fraction of each object's reference value at which to cut.
    sigma : float, tuple or None
        Gaussian sigma in pixels for smoothing the image the reference value is
        read from. If None, the value at the seed pixel is used.

    Returns
    -------
    label : array
        The labeled image with each object trimmed.
    """
    label = np.asarray(label)
    image = np.asarray(image)
    points = np.asarray(seeds).reshape(-1, image.ndim)
    n_seeds = len(points)
    if n_seeds == 0:
        return np.zeros_like(label)
    points = np.clip(seed_pixels(points), 0, np.array(image.shape) - 1)

    smoothed = image if sigma is None else scipy.ndimage.gaussian_filter(image.astype(float), sigma)
    level = np.full(max(int(label.max()), n_seeds) + 1, np.inf)
    level[1:n_seeds + 1] = fraction * smoothed[tuple(points.T)]
    keep = (label > 0) & (image >= level[label])

    # Keep only the part of each object connected to its own seed.
    components, _ = scipy.ndimage.label(keep)
    at_seed = np.zeros(len(level), dtype=components.dtype)
    at_seed[1:n_seeds + 1] = components[tuple(points.T)]
    keep &= components == at_seed[label]
    return np.where(keep, label, 0)


def find_size(label, max_label=None, verbose=False):
    """
    Find size given object shapes as a labled image

    Arguments
    ---------
    label : array, str or Source
        Labeled image in which each object has its own label.
    max_label : int or None
        Maximal label to include, if None use all label.
    verbose : bool
        Print progress info.

    Returns
    -------
    sizes : array
        Measured intensities
    """

    if verbose:
        timer = tmr.Timer()
        hdict.pprint(head='Size detection:', max_label=max_label)

    label = io.as_source(label)

    if max_label is None:
        max_label = int(label.max())

    sizes = scipy.ndimage.measurements.sum(np.ones(label.shape, dtype=bool),
                                           labels=label, index=np.arange(1, max_label + 1))

    if verbose:
        timer.print_elapsed_time(head='Size detection')

    return sizes


def find_intensity(source, label, max_label=None, method='sum', verbose=False):
    """
    Find integrated intensity given object shapes as labeled image.

    Arguments
    ---------
    source : array, str, or Source
      Source to measure intensities from.
    label : array, str, or Source
      Labeled image with a separate label for each object.
    max_label : int or None
      Maximal label to include. If None, use all.
    method : {'sum', 'mean', 'max', 'min'}
      Method to use to measure the intensities in each object's area.
    verbose : bool
      If True, print progress information.

    Returns
    -------
    intensities : array
      Measured intensities.
    """
    method = method.lower()
    if verbose:
        timer = tmr.Timer()
        hdict.pprint(head='Intensity detection:', max_label=max_label, method=method)

    source = io.as_source(source).array
    label = io.as_source(label)

    if max_label is None:
        max_label = label.max()

    measure_functions = {
      'sum': scipy.ndimage.measurements.sum,
      'mean': scipy.ndimage.measurements.mean,
      'max': scipy.ndimage.measurements.maximum,
      'min': scipy.ndimage.measurements.minimum
    }

    try:
        intensities = measure_functions[method](source, labels=label, index=np.arange(1, max_label + 1))
    except KeyError:
        raise RuntimeError(f'Unknown method {method}, expected one of {measure_functions.keys()}')

    if verbose:
        timer.print_elapsed_time(head='Intensity detection')

    return intensities
  