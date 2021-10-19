# -*- coding: utf-8 -*-
"""Test Multipath Fading Channel Model Templates."""

import unittest
from unittest.mock import Mock

from channel import MultipathFadingCost256, MultipathFading5GTDL

__author__ = "Jan Adler"
__copyright__ = "Copyright 2021, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "0.1.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class TestCost256(unittest.TestCase):
    """Test the Cost256 template for the multipath fading channel model."""

    def setUp(self) -> None:

        self.transmitter = Mock()
        self.receiver = Mock()
        self.transmitter.num_antennas = 1
        self.receiver.num_antennas = 1

    def test_init(self) -> None:
        """Test the template initializations."""

        for model_type in MultipathFadingCost256.TYPE:

            channel = MultipathFadingCost256(model_type,
                                             self.transmitter,
                                             self.receiver)

            self.assertIs(self.transmitter, channel.transmitter)
            self.assertIs(self.receiver, channel.receiver)

    def test_init_validation(self) -> None:
        """Template initialization should raise ValueError on invalid model type."""

        with self.assertRaises(ValueError):
            _ = MultipathFadingCost256(100000)

        with self.assertRaises(ValueError):
            _ = MultipathFadingCost256(MultipathFadingCost256.TYPE.HILLY, los_angle=0.0)

    def test_model_type(self) -> None:
        """The model type property should return """

        for model_type in MultipathFadingCost256.TYPE:

            channel = MultipathFadingCost256(model_type)
            self.assertEqual(model_type, channel.model_type)


class Test5GTDL(unittest.TestCase):
    """Test the 5GTDL template for the multipath fading channel model."""

    def setUp(self) -> None:

        self.transmitter = Mock()
        self.receiver = Mock()
        self.transmitter.num_antennas = 1
        self.receiver.num_antennas = 1

    def test_init(self) -> None:
        """Test the template initializations."""

        for model_type in MultipathFadingCost256.TYPE:

            channel = MultipathFading5GTDL(model_type,
                                           self.transmitter,
                                           self.receiver)

            self.assertIs(self.transmitter, channel.transmitter)
            self.assertIs(self.receiver, channel.receiver)

    def test_init_validation(self) -> None:
        """Template initialization should raise ValueError on invalid model type."""

        with self.assertRaises(ValueError):
            _ = MultipathFading5GTDL(100000)

        with self.assertRaises(ValueError):
            _ = MultipathFading5GTDL(MultipathFading5GTDL.TYPE.D, los_doppler_frequency=0.0)

        with self.assertRaises(ValueError):
            _ = MultipathFading5GTDL(MultipathFading5GTDL.TYPE.E, los_doppler_frequency=0.0)

    def test_model_type(self) -> None:
        """The model type property should return """

        for model_type in MultipathFadingCost256.TYPE:

            channel = MultipathFading5GTDL(model_type)
            self.assertEqual(model_type, channel.model_type)