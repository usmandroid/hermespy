# -*- coding: utf-8 -*-

from __future__ import annotations
from abc import ABC, abstractmethod
from fractions import Fraction
from typing import TYPE_CHECKING

from hermespy.core import Serializable
from hermespy.precoding.precoding import Precoder, Precoding

from ..symbols import StatedSymbols

if TYPE_CHECKING:
    from ..modem import BaseModem  # pragma: no cover

__author__ = "Jan Adler"
__copyright__ = "Copyright 2023, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "1.1.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class SymbolPrecoder(Precoder, ABC):
    """Abstract base class for signal processing algorithms operating on complex data symbols streams.

    A symbol precoder represents one coding step of a full symbol precoding configuration.
    It features the `encoding` and `decoding` routines, meant to encode and decode multidimensional symbol streams
    during transmission and reception, respectively.
    """

    @abstractmethod
    def encode(self, symbols: StatedSymbols) -> StatedSymbols:
        """Encode a data stream before transmission.

        This operation may modify the number of streams as well as the number of data symbols per stream.

        Args:

            symbols (StatedSymbols):
                Symbols to be encoded.

        Returns: Encoded symbols.

        Raises:

            NotImplementedError: If an encoding operation is not supported.
        """
        ...  # pragma no cover

    @abstractmethod
    def decode(self, symbols: StatedSymbols) -> StatedSymbols:
        """Decode a data stream before reception.

        This operation may modify the number of streams as well as the number of data symbols per stream.

        Args:

            symbols (Symbols):
                Symbols to be decoded.

        Returns: Decoded symbols.

        Raises:

            NotImplementedError: If a decoding operation is not supported.
        """
        ...  # pragma no cover


class SymbolPrecoding(Precoding[SymbolPrecoder], Serializable):
    """Channel SymbolPrecoding configuration for wireless transmission of modulated data symbols.

    Symbol precoding may occur as an intermediate step between bit-mapping and base-band symbol modulations.
    In order to account for the possibility of multiple antenna data-streams,
    waveform generators may access the `SymbolPrecoding` configuration to encode one-dimensional symbol
    streams into multi-dimensional symbol streams during transmission and subsequently decode during reception.
    """

    yaml_tag = "SymbolCoding"

    def __init__(self, modem: BaseModem | None = None) -> None:
        """Symbol Precoding object initialization.

        Args:

            modem (BaseModem, optional):
                The modem this :class:`SymbolPrecoding` configuration is attached to.
        """

        Precoding.__init__(self, modem=modem)

    def encode(self, symbols: StatedSymbols) -> StatedSymbols:
        """Encode a data stream before transmission.

        This operation may modify the number of streams as well as the number of data symbols per stream.

        Args:

            symbols (StatedSymbols): Symbols to be encoded.

        Returns: Encoded symbols.

        Raises:

            NotImplementedError: If an encoding operation is not supported.
        """

        # Iteratively apply each encoding step
        encoded_symbols = symbols.copy()
        for precoder in self:
            encoded_symbols = precoder.encode(encoded_symbols)

        return encoded_symbols

    def decode(self, symbols: StatedSymbols) -> StatedSymbols:
        """Decode a data stream before reception.

        This operation may modify the number of streams as well as the number of data symbols per stream.

        Args:

            symbols (StatedSymbols):
                Symbols to be decoded.

        Returns: Decoded symbols.

        Raises:

            NotImplementedError: If an encoding operation is not supported.
        """

        decoded_symbols = symbols.copy()
        for precoder in reversed(self):
            decoded_symbols = precoder.decode(decoded_symbols)

        return decoded_symbols

    def num_encoded_blocks(self, num_input_blocks: int) -> int:
        """Number of blocks after encoding.

        Args:

            num_input_blocks (int):
                Number of blocks before encoding.

        Returns: Number of blocks after encoding.
        """

        num_blocks = Fraction(num_input_blocks, 1)

        for precoder in self:
            num_blocks /= precoder.rate

        return int(num_blocks)
