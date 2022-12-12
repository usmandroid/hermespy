# -*- coding: utf-8 -*-
"""
====================
Phase Noise Modeling
====================
"""

from abc import ABC, abstractmethod

from hermespy.core import RandomNode, Serializable, Signal

__author__ = "Jan Adler"
__copyright__ = "Copyright 2022, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "1.0.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class PhaseNoise(RandomNode, ABC):
    """Base class of phase noise models."""

    @abstractmethod
    def add_noise(self, signal: Signal) -> Signal:
        """Add phase noise to a signal model.

        Args:

            signal (Signal):
                The signal model to which phase noise is to be added.

        Returns: Noise signal model.
        """
        ...  # pragma no cover


class NoPhaseNoise(PhaseNoise, Serializable):
    """No phase noise considered within the device model."""

    yaml_tag = "NoPhaseNoise"
    """YAML serialization tag"""

    def add_noise(self, signal: Signal) -> Signal:

        # It's just a stub
        return signal
