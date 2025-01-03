# -*- coding: utf-8 -*-
"""
===============
Extra Operators
===============

This module contains convenience operators not part of the standard library.
"""

from __future__ import annotations

import numpy as np
from h5py import Group

from .definitions import SNRType
from .device import Transmission, Transmitter, Receiver, Reception
from .signal_model import Signal

__author__ = "Jan Adler"
__copyright__ = "Copyright 2023, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "1.2.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class StaticOperator(object):
    """Base class for static device operators"""

    __num_samples: int  # Number of samples per transmission
    __sampling_rate: float  # Sampling rate of transmission

    def __init__(self, num_samples: int, sampling_rate: float) -> None:
        """
        Args:

            num_samples (int):
                Number of samples per transmission.

            sampling_rate (float):
                Sampling rate of transmission.
        """

        self.__num_samples = num_samples
        self.sampling_rate = sampling_rate

    @property
    def num_samples(self) -> int:
        """Number of samples per transmission.

        Returns: Number of samples.
        """

        return self.__num_samples

    @property
    def sampling_rate(self) -> float:
        return self.__sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"Sampling rate must be positive (not {value})")

        self.__sampling_rate = value

    @property
    def frame_duration(self) -> float:
        return self.__num_samples / self.sampling_rate


class SilentTransmitter(StaticOperator, Transmitter[Transmission]):
    """Silent transmitter mock."""

    yaml_tag = "SilentTransmitter"
    serialized_attributes = {"num_samples", "sampling_rate", "device"}

    def __init__(self, num_samples: int, sampling_rate: float, *args, **kwargs) -> None:
        """
        Args:

            num_samples (int):
                Number of samples per transmission.

            sampling_rate (float):
                Sampling rate of transmission.
        """

        # Init base classes
        StaticOperator.__init__(self, num_samples, sampling_rate)
        Transmitter.__init__(self, *args, **kwargs)

    def _transmit(self, duration: float = 0.0) -> Transmission:
        # Compute the number of samples to be transmitted
        num_samples = self.num_samples if duration <= 0.0 else int(duration * self.sampling_rate)

        silence = Signal(
            np.zeros((self.device.num_antennas, num_samples), dtype=complex),
            sampling_rate=self.sampling_rate,
            carrier_frequency=self.device.carrier_frequency,
        )

        transmission = Transmission(silence)

        self.device.transmitters.add_transmission(self, transmission)
        return transmission

    def _recall_transmission(self, group: Group) -> Transmission:
        return Transmission.from_HDF(group)


class SignalTransmitter(StaticOperator, Transmitter[Transmission]):
    """Custom signal transmitter."""

    yaml_tag = "SignalTransmitter"

    __signal: Signal

    def __init__(self, signal: Signal, *args, **kwargs) -> None:
        """
        Args:

            signal (Signal):
                Signal to be transmittered by the static operator for each transmission.
        """

        # Init base classes
        StaticOperator.__init__(self, signal.num_samples, signal.sampling_rate)
        Transmitter.__init__(self, *args, **kwargs)

        # Init class attributes
        self.__signal = signal

    @property
    def signal(self) -> Signal:
        """Signal to be transmitted by the static operator for each transmission."""

        return self.__signal

    @signal.setter
    def signal(self, value: Signal) -> None:
        self.__signal = value

    def _transmit(self, duration: float = 0.0) -> Transmission:
        transmission = Transmission(self.__signal)
        return transmission

    def _recall_transmission(self, group: Group) -> Transmission:
        return Transmission.from_HDF(group)


class SignalReceiver(StaticOperator, Receiver[Reception]):
    """Custom signal receiver."""

    yaml_tag = "SignalReceiver"
    serialized_attributes = {"num_samples", "sampling_rate", "device"}

    __expected_power: float

    def __init__(
        self, num_samples: int, sampling_rate: float, expected_power: float = 0.0, *args, **kwargs
    ) -> None:
        # Initialize base classes
        StaticOperator.__init__(self, num_samples, sampling_rate)
        Receiver.__init__(self, *args, **kwargs)

        # Initialize class attributes
        if expected_power < 0.0:
            raise ValueError(f"Expected power must be non-negative (not {expected_power})")
        self.__expected_power = expected_power

    @property
    def energy(self) -> float:
        return self.__expected_power * self.num_samples

    def _receive(self, signal: Signal) -> Reception:
        received_signal = signal.resample(self.sampling_rate)
        return Reception(received_signal)

    def _noise_power(self, strength: float, snr_type: SNRType) -> float:
        if snr_type == SNRType.PN0:
            return self.__expected_power / strength

        if snr_type == SNRType.EN0:
            return self.__expected_power / strength * self.num_samples

        raise ValueError(f"SNR type {snr_type} is not supported by the SignalReceiver")

    def _recall_reception(self, group: Group) -> Reception:
        return Reception.from_HDF(group)
