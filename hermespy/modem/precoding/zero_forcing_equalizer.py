# -*- coding: utf-8 -*-
"""Zero-Forcing channel equalization."""

from __future__ import annotations
from typing import Type, Tuple
from ruamel.yaml import SafeRepresenter, SafeConstructor, ScalarNode
import numpy as np

from .symbol_precoder import SymbolPrecoder

__author__ = "Tobias Kronauer"
__copyright__ = "Copyright 2021, Barkhausen Institut gGmbH"
__credits__ = ["Tobias Kronauer", "Jan Adler"]
__license__ = "AGPLv3"
__version__ = "0.2.0"
__maintainer__ = "Tobias Kronauer"
__email__ = "tobias.kronauer@barkhauseninstitut.org"
__status__ = "Prototype"


class ZeroForcingEqualizer(SymbolPrecoder):
    """Zero-Forcing channel equalization."""

    yaml_tag: str = u'ZF'

    def __init__(self) -> None:
        """Zero-Forcing channel equalization object initialization."""

        SymbolPrecoder.__init__(self)

    def encode(self, symbol_stream: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Equalization can only applied to receiver stream coding configurations")

    def decode(self,
               symbol_stream: np.ndarray,
               stream_responses: np.ndarray,
               stream_noises: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:

        equalized_symbols = np.empty(symbol_stream.shape, dtype=complex)
        equalized_responses = np.empty(stream_responses.shape, dtype=complex)
        equalized_noises = np.empty(stream_noises.shape, dtype=complex)

        for idx, (symbol, response, noise) in enumerate(zip(symbol_stream.T,
                                                            np.rollaxis(stream_responses, 1),
                                                            np.rollaxis(stream_noises, 1))):
            noise_covariance = np.diag(noise)
            equalizer = np.linalg.pinv(response)

            equalized_symbols[:, idx] = equalizer @ symbol
            equalized_responses[:, idx, :] = equalizer @ response
            equalized_noises[:, idx] = np.diag(equalized_responses[:, idx, :] @ noise_covariance).real ** -1 - 1

        return equalized_symbols, equalized_responses, equalized_noises

    @property
    def num_input_streams(self) -> int:
        return self.required_num_output_streams

    @property
    def num_output_streams(self) -> int:
        return self.required_num_input_streams

    @classmethod
    def to_yaml(cls: Type[ZeroForcingEqualizer],
                representer: SafeRepresenter,
                node: ZeroForcingEqualizer) -> ScalarNode:
        """Serialize an `ZeroForcingEqualizer` object to YAML.

        Args:
            representer (SafeRepresenter):
                A handle to a representer used to generate valid YAML code.
                The representer gets passed down the serialization tree to each node.

            node (ZeroForcingEqualizer):
                The `ZeroForcingEqualizer` instance to be serialized.

        Returns:
            Node:
                The serialized YAML node
        """

        return representer.represent_scalar(cls.yaml_tag, None)

    @classmethod
    def from_yaml(cls: Type[ZeroForcingEqualizer],
                  constructor: SafeConstructor,
                  node: ScalarNode) -> ZeroForcingEqualizer:
        """Recall a new `ZeroForcingEqualizer` instance from YAML.

        Args:
            constructor (SafeConstructor):
                A handle to the constructor extracting the YAML information.

            node (Node):
                YAML node representing the `ZeroForcingEqualizer` serialization.

        Returns:
            ZeroForcingEqualizer:
                Newly created `ZeroForcingEqualizer` instance.
        """

        return cls()
