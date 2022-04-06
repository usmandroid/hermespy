from __future__ import annotations
from typing import Optional, Tuple

import numpy as np
from scipy.constants import speed_of_light
from scipy.signal import correlate

from hermespy.core.signal_model import Signal
from hermespy.modem import Modem, Symbols
from hermespy.radar import Radar
from hermespy.radar.radar import RadarCube

__author__ = "Jan Adler"
__copyright__ = "Copyright 2022, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "Jan Adler"
__version__ = "0.2.7"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class MatchedFilterJcas(Modem, Radar):
    """Joint Communication and Sensing Operator."""
    
    __transmission: Optional[Signal]        # Most recent transmission
    __sampling_rate: Optional[float]        # The specific required sampling rate
    __max_range: float                      # Maximally detectable range
    
    def __init__(self, max_range: float) -> None:
        """
        Args:
        
            max_range (float):
                Maximally detectable range in m.
        """
        
        self.__sampling_rate = None
        self.max_range = max_range
        
        Modem.__init__(self)
        Radar.__init__(self)

    def transmit(self, duration: float = 0) -> Tuple[Signal, Symbols, np.ndarray]:
        
        # Cache the recently transmitted waveform for correlation during reception
        signal, symbols, bits =  super().transmit(duration)
        
        # Resample the signal for an improved range resolution visualization
        # Cache the resampled transmission
        self.__transmission = signal.resample(self.sampling_rate)
        
        return signal, symbols, bits
        
    def receive(self) -> Tuple[Signal, Symbols, np.ndarray, RadarCube]:
        
        # There must be a recent transmission being cached in order to correlate
        if self.__transmission is None:
            raise RuntimeError("Receiving from a matched filter joint must be preceeded by a transmission")
        
        # Receive information
        signal, symbols, bits = Modem.receive(self)
        
        # Re-sample communication waveform
        resampled_signal = signal.resample(self.sampling_rate)
        
        correlation = abs(correlate(resampled_signal.samples, self.__transmission.samples, mode='valid', method='fft').flatten()) / self.__transmission.num_samples
        
        # Append zeros for correct depth estimation
        num_samples = int(2 * self.max_range / speed_of_light * self.sampling_rate)
        num_appended_zeros = max(0, num_samples - resampled_signal.num_samples)
        correlation = np.append(correlation, np.zeros(num_appended_zeros))

        angle_bins = np.array([0.])
        velocity_bins = np.array([0.])
        range_bins = .5 * np.arange(len(correlation)) * speed_of_light / resampled_signal.sampling_rate
        cube_data = np.array([[correlation]], dtype=float)
        cube = RadarCube(cube_data, angle_bins, velocity_bins, range_bins)

        return signal, symbols, bits, cube
        
    @property
    def sampling_rate(self) -> float:
        
        modem_sampling_rate = self.waveform_generator.sampling_rate
        
        if self.__sampling_rate is None:
            return modem_sampling_rate
        
        return max(modem_sampling_rate, self.__sampling_rate)
        
    @sampling_rate.setter
    def sampling_rate(self, value: Optional[float]) -> None:
        
        if value is None:
            
            self.__sampling_rate = None
            return
        
        if value <= 0.:
            raise ValueError("Sampling rate must be greater than zero")
        
        self.__sampling_rate = value
        
    @property
    def range_resolution(self) -> float:
        """Resolution of the Range Estimation.
        
        Returns:
            float:
                Resolution in m.
                
        Raises:
        
            ValueError:
                If the range resolution is smaller or equal to zero.
        """
        
        
        return speed_of_light / self.sampling_rate
    
    @range_resolution.setter
    def range_resolution(self, value: float) -> None:
        
        if value <= 0.:
            raise ValueError("Range resolution must be greater than zero")
        
        self.sampling_rate = speed_of_light / value
    
    @property
    def max_range(self) -> float:
        """Maximally Estimated Range.
        
        Returns:
            The maximum range in m.
            
        Raises:
        
            ValueError:
                If `max_range` is smaller or equal to zero.
        """
        
        return self.__max_range
        
    @max_range.setter
    def max_range(self, value) -> None:
        
        if value <= 0.:
            raise ValueError("Maximum range must be greater than zero")
        
        self.__max_range = value