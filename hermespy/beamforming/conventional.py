# -*- coding: utf-8 -*-
"""
=======================
Conventional Beamformer
=======================

Also refererd to as Delay and Sum Beamformer.
"""

from typing import Optional

import numpy as np
from numba import jit
from scipy.constants import pi, speed_of_light

from hermespy.core import AntennaArray, Direction, DuplexOperator, Serializable
from .beamformer import TransmitBeamformer, ReceiveBeamformer


__author__ = "Jan Adler"
__copyright__ = "Copyright 2023, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "1.2.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class ConventionalBeamformer(Serializable, TransmitBeamformer, ReceiveBeamformer):
    """Conventional delay and sum beamforming.

    The Bartlett\\ :footcite:`1950:bartlett` beamformer,
    also known as conventional or delay and sum beamformer,
    maximizes the power transmitted or received towards a single direction of interest
    :math:`(\\theta, \\phi)`, where :math:`\\theta` is the zenith and :math:`\\phi`  is the azimuth angle of interest in spherical coordinates, respectively.

    Let :math:`\\mathbf{X} \in \mathbb{C}^{N \\times T}` be the the matrix of :math:`T` time-discrete samples acquired by an antenna arrary featuring :math:`N` antennas.
    The antenna array's response towards a source within its far field emitting a signal of small relative bandwidth is :math:`\\mathbf{a}(\\theta, \\phi) \\in \\mathbb{C}^{N}`.
    Then

    .. math::

        \\hat{P}_{\\mathrm{Capon}}(\\theta, \\phi) = \\mathbf{a}^\\mathsf{H}(\\theta, \\phi)  \\mathbf{X} \\mathbf{X}^\\mathsf{H} \\mathbf{a}(\\theta, \\phi)

    is the Conventional beamformer's power estimate     with

    .. math::

       \\mathbf{w}(\\theta, \\phi) = \\mathbf{a}(\\theta, \\phi)

    being the beamforming weights to steer the sensor array's receive characteristics towards direction :math:`(\\theta, \\phi)`, so that

    .. math::

       \\mathcal{B}\\lbrace \\mathbf{X} \\rbrace = \\mathbf{w}^\\mathsf{H}(\\theta, \\phi) \\mathbf{X}

    is the implemented beamforming equation.
    """

    yaml_tag = "ConventionalBeamformer"
    """YAML serialization tag."""

    def __init__(self, operator: Optional[DuplexOperator] = None) -> None:
        TransmitBeamformer.__init__(self, operator=operator)
        ReceiveBeamformer.__init__(self, operator=operator)

    @property
    def num_receive_focus_points(self) -> int:
        # The conventional beamformer focuses a single angle
        return 1

    @property
    def num_receive_input_streams(self) -> int:
        # The conventional beamformer will allways consider all antennas streams
        return self.operator.device.antennas.num_receive_ports

    @property
    def num_receive_output_streams(self) -> int:
        # The convetional beamformer will always return a single stream,
        # combining all antenna signals into one
        return 1

    @property
    def num_transmit_focus_points(self) -> int:
        # The conventional beamformer focuses a single angle
        return 1

    @property
    def num_transmit_output_streams(self) -> int:
        # The conventional beamformer will allways consider all antennas streams
        return self.operator.device.antennas.num_transmit_ports

    @property
    def num_transmit_input_streams(self) -> int:
        # The convetional beamformer will always return a single stream,
        # combining all antenna signals into one
        return 1

    # @lru_cache(maxsize=2)
    def _codebook(
        self, carrier_frequency: float, angles: np.ndarray, array: AntennaArray
    ) -> np.ndarray:
        """Compute the beamforming codebook for a given set of angles of interest.

        Args:

            carrier_frequency (float):
                The assumed carrier central frequency of the samples.

            angles (numpy.ndarray):
                Spherical coordinate system angles of arrival in radians.
                A two dimensional numpy array with the first dimension representing the number of angles,
                and the second dimension of magnitude two containing the azimuth and zenith angle in radians, respectively.

            array (AntennaArray):
                The antenna array to compute the codebook for.

        Returns:

            The codebook represented by a two-dimensional numpy array,
            with the first dimension being the number of angles and the second dimension the number of antennas.
        """

        # Query topology of receiving antenna ports
        topology = (
            np.array([p.global_position for p in array.receive_ports], dtype=np.float_)
            - array.global_position
        )

        # Build receive beamforming codebook of steering vectors for each angle of interest
        book = np.empty((angles.shape[0], array.num_receive_ports), dtype=complex)
        for n, (azimuth, zenith) in enumerate(angles):
            direction = Direction.From_Spherical(azimuth, zenith)
            weights = np.exp(
                1j * 2 * pi * carrier_frequency / speed_of_light * (topology @ direction)
            )
            book[n, :] = weights

        return book / array.num_receive_ports

    def _encode(
        self,
        samples: np.ndarray,
        carrier_frequency: float,
        focus_angles: np.ndarray,
        array: AntennaArray,
    ) -> np.ndarray:
        azimuth, zenith = focus_angles[0, :]

        # Compute conventional beamformer weights
        topology = (
            np.array([p.global_position for p in array.transmit_ports], dtype=np.float_)
            - array.global_position
        )
        direction = Direction.From_Spherical(azimuth, zenith)
        weights = np.exp(-1j * 2 * pi * carrier_frequency / speed_of_light * (topology @ direction))

        # Weight the streams accordingly
        samples = weights[:, np.newaxis] @ samples

        # That's it
        return samples

    @staticmethod
    @jit(nopython=True)
    def _beamform(
        codebook: np.ndarray, samples: np.ndarray, conjugate: bool = False
    ) -> np.ndarray:  # pragma: no cover
        if conjugate:
            return codebook.conj() @ samples

        else:
            return codebook @ samples

    def _decode(
        self, samples: np.ndarray, carrier_frequency: float, angles: np.ndarray, array: AntennaArray
    ) -> np.ndarray:
        codebook = self._codebook(carrier_frequency, angles[:, 0, :], array)
        beamformed_samples = self._beamform(codebook, samples, True)

        return beamformed_samples[:, np.newaxis, :]
