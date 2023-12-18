# -*- coding: utf-8 -*-

from __future__ import annotations
from abc import ABC
from collections.abc import Sequence

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import uniform

from hermespy.core import (
    ArtifactTemplate,
    Serializable,
    Evaluator,
    EvaluationTemplate,
    GridDimension,
    ScalarEvaluationResult,
    VAT,
)
from .modem import TransmittingModem, ReceivingModem

__author__ = "Jan Adler"
__copyright__ = "Copyright 2023, Barkhausen Institut gGmbH"
__credits__ = ["Jan Adler"]
__license__ = "AGPLv3"
__version__ = "1.2.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


class CommunicationEvaluator(Evaluator, ABC):
    """Base class for evaluating communication processes between two modems."""

    __transmitting_modem: TransmittingModem  # Handle to the transmitting modem
    __receiving_modem: ReceivingModem  # Handle to the receiving modem
    __plot_surface: bool

    def __init__(
        self,
        transmitting_modem: TransmittingModem,
        receiving_modem: ReceivingModem,
        plot_surface: bool = True,
    ) -> None:
        """
        Args:

            transmitting_modem (TransmittingModem):
                Modem transmitting information.

            receiving_modem (ReceivingModem):
                Modem receiving information.

            plot_surface (bool, optional):
                Plot the surface of the evaluation result in two-dimensional grids.
                Defaults to True.
        """

        self.__transmitting_modem = transmitting_modem
        self.__receiving_modem = receiving_modem
        self.__plot_surface = plot_surface

        # Initialize base class
        Evaluator.__init__(self)

    @property
    def transmitting_modem(self) -> TransmittingModem:
        """Modem transmitting information.

        Denoted by :math:`(\\alpha)` within the respective equations.
        """

        return self.__transmitting_modem

    @property
    def receiving_modem(self) -> ReceivingModem:
        """Modem receiving information.

        Denoted by :math:`(\\beta)` within the respective equations.
        """

        return self.__receiving_modem

    def generate_result(
        self, grid: Sequence[GridDimension], artifacts: np.ndarray
    ) -> ScalarEvaluationResult:
        return ScalarEvaluationResult.From_Artifacts(grid, artifacts, self, self.__plot_surface)


class BitErrorArtifact(ArtifactTemplate[np.float_]):
    """Artifact of a bit error evaluation between two modems exchanging information.

    Generated by :meth:`artifact()<BitErrorEvaluation.artifact>` of :class:`BitErrorEvaluation`.
    """
    ...  # pragma: no cover


class BitErrorEvaluation(EvaluationTemplate[np.ndarray]):
    """Bit error evaluation between two modems exchanging information.

    Generated by :meth:`evaluate()<BitErrorEvaluator.evaluate>` of :class:`BitErrorEvaluator`.
    """

    @property
    def title(self) -> str:
        return "Bit Error Evaluation"

    def _plot(self, axes: VAT) -> None:
        ax: plt.Axes = axes.flat[0]
        ax.stem(self.evaluation)
        ax.set_xlabel("Bit Index")
        ax.set_ylabel("Bit Error Indicator")

    def artifact(self) -> BitErrorArtifact:
        ber = np.mean(self.evaluation)
        return BitErrorArtifact(ber)


class BitErrorEvaluator(CommunicationEvaluator, Serializable):
    """Evaluate bit errors between two modems exchanging information."""

    yaml_tag = "BitErrorEvaluator"

    def __init__(
        self,
        transmitting_modem: TransmittingModem,
        receiving_modem: ReceivingModem,
        plot_surface: bool = True,
    ) -> None:
        """
        Args:

            transmitting_modem (TransmittingModem):
                Modem transmitting information.

            receiving_modem (ReceivingModem):
                Modem receiving information.

            plot_surface (bool, optional):
                Plot the surface of the evaluation result in two-dimensional grids.
                Defaults to True.
        """

        CommunicationEvaluator.__init__(self, transmitting_modem, receiving_modem, plot_surface)
        self.plot_scale = "log"  # Plot logarithmically by default

    def evaluate(self) -> BitErrorEvaluation:
        # Retrieve transmitted and received bits
        transmitted_bits = self.transmitting_modem.transmission.bits
        received_bits = self.receiving_modem.reception.bits

        # Pad bit sequences (if required)
        num_bits = max(len(received_bits), len(transmitted_bits))
        padded_transmission = np.append(
            transmitted_bits, np.zeros(num_bits - len(transmitted_bits))
        )
        padded_reception = np.append(received_bits, np.zeros(num_bits - len(received_bits)))

        # Compute bit errors as the positions where both sequences differ.
        # Note that this requires the sequences to be in 0/1 format!
        bit_errors = np.abs(padded_transmission - padded_reception)

        return BitErrorEvaluation(bit_errors)

    @property
    def abbreviation(self) -> str:
        return "BER"

    @property
    def title(self) -> str:
        return "Bit Error Rate Evaluation"

    @staticmethod
    def _scalar_cdf(scalar: float) -> float:
        return uniform.cdf(scalar)


class BlockErrorArtifact(ArtifactTemplate[np.float_]):
    """Artifact of a block error evaluation between two modems exchanging information."""

    ...  # pragma: no cover


class BlockErrorEvaluation(EvaluationTemplate[np.ndarray]):
    """Block error evaluation of a single communication process between modems."""

    @property
    def title(self) -> str:
        return "Block Error Evaluation"

    def _plot(self, axes: VAT) -> None:
        ax: plt.Axes = axes.flat[0]
        ax.stem(self.evaluation)
        ax.set_xlabel("Block Index")
        ax.set_ylabel("Block Error Indicator")

    def artifact(self) -> BlockErrorArtifact:
        bler = np.mean(self.evaluation)
        return BlockErrorArtifact(bler)


class BlockErrorEvaluator(CommunicationEvaluator, Serializable):
    """Evaluate block errors between two modems exchanging information."""

    yaml_tag = "BlockErrorEvaluator"

    def __init__(
        self,
        transmitting_modem: TransmittingModem,
        receiving_modem: ReceivingModem,
        plot_surface: bool = True,
    ) -> None:
        """
        Args:

            transmitting_modem (TransmittingModem):
                Modem transmitting information.

            receiving_modem (ReceivingModem):
                Modem receiving information.

            plot_surface (bool, optional):
                Plot the surface of the evaluation result in two-dimensional grids.
                Defaults to True.
        """

        CommunicationEvaluator.__init__(self, transmitting_modem, receiving_modem, plot_surface)
        self.plot_scale = "log"  # Plot logarithmically by default

    def evaluate(self) -> BlockErrorEvaluation:
        # Retrieve transmitted and received bits
        transmitted_bits = self.transmitting_modem.transmission.bits
        received_bits = self.receiving_modem.reception.bits
        block_size = self.receiving_modem.encoder_manager.bit_block_size

        # Pad bit sequences (if required)
        received_bits = np.append(received_bits, np.zeros(received_bits.shape[0] % block_size))

        if transmitted_bits.shape[0] >= received_bits.shape[0]:
            transmitted_bits = transmitted_bits[: received_bits.shape[0]]

        else:
            transmitted_bits = np.append(
                transmitted_bits, -np.ones(received_bits.shape[0] - transmitted_bits.shape[0])
            )

        # Compute bit errors as the positions where both sequences differ.
        # Note that this requires the sequences to be in 0/1 format!
        bit_errors = np.abs(transmitted_bits - received_bits)
        block_errors = bit_errors.reshape((-1, block_size)).sum(axis=1) > 0

        return BlockErrorEvaluation(block_errors)

    @property
    def title(self) -> str:
        return "Block Error Rate"

    @property
    def abbreviation(self) -> str:
        return "BLER"

    @staticmethod
    def _scalar_cdf(scalar: float) -> float:
        return uniform.cdf(scalar)


class FrameErrorArtifact(ArtifactTemplate[float]):
    """Artifact of a frame error evaluation between two modems exchanging information."""

    ...  # pragma: no cover


class FrameErrorEvaluation(EvaluationTemplate[np.ndarray]):
    """Frame error evaluation of a single communication process between modems."""

    @property
    def title(self) -> str:
        return "Frame Error Evaluation"

    def _plot(self, axes: VAT) -> None:
        ax: plt.Axes = axes.flat[0]
        ax.stem(self.evaluation)
        ax.set_xlabel("Frame Index")
        ax.set_ylabel("Frame Error Indicator")

    def artifact(self) -> FrameErrorArtifact:
        bler = float(np.mean(self.evaluation))
        return FrameErrorArtifact(bler)


class FrameErrorEvaluator(CommunicationEvaluator, Serializable):
    """Evaluate frame errors between two modems exchanging information."""

    yaml_tag = "FrameErrorEvaluator"
    """YAML serialization tag"""

    def __init__(
        self,
        transmitting_modem: TransmittingModem,
        receiving_modem: ReceivingModem,
        plot_surface: bool = True,
    ) -> None:
        """
        Args:

            transmitting_modem (TransmittingModem):
                Modem transmitting information.

            receiving_modem (ReceivingModem):
                Modem receiving information.

            plot_surface (bool, optional):
                Plot the surface of the evaluation result in two-dimensional grids.
                Defaults to True.
        """

        CommunicationEvaluator.__init__(self, transmitting_modem, receiving_modem, plot_surface)
        self.plot_scale = "log"  # Plot logarithmically by default

    def evaluate(self) -> FrameErrorEvaluation:
        # Retrieve transmitted and received bits
        transmitted_bits = self.transmitting_modem.transmission.bits
        received_bits = self.receiving_modem.reception.bits
        frame_size = self.receiving_modem.num_data_bits_per_frame

        if frame_size < 1:
            return FrameErrorEvaluation(np.empty(0, dtype=np.int_))

        # Pad bit sequences (if required)
        received_bits = np.append(received_bits, np.zeros(received_bits.shape[0] % frame_size))

        if transmitted_bits.shape[0] >= received_bits.shape[0]:
            transmitted_bits = transmitted_bits[: received_bits.shape[0]]

        else:
            transmitted_bits = np.append(
                transmitted_bits, -np.ones(received_bits.shape[0] - transmitted_bits.shape[0])
            )

        # Compute bit errors as the positions where both sequences differ.
        # Note that this requires the sequences to be in 0/1 format!
        bit_errors = np.abs(transmitted_bits - received_bits)
        frame_errors = bit_errors.reshape((-1, frame_size)).sum(axis=1) > 0

        return FrameErrorEvaluation(frame_errors)

    @property
    def title(self) -> str:
        return "Frame Error Rate"

    @property
    def abbreviation(self) -> str:
        return "FER"

    @staticmethod
    def _scalar_cdf(scalar: float) -> float:
        return uniform.cdf(scalar)


class ThroughputArtifact(ArtifactTemplate[float]):
    """Artifact of a throughput evaluation between two modems exchanging information."""

    ...  # pragma: no cover


class ThroughputEvaluation(EvaluationTemplate[float]):
    """Throughput evaluation between two modems exchanging information."""

    def __init__(
        self, bits_per_frame: int, frame_duration: float, frame_errors: np.ndarray
    ) -> None:
        """
        Args:

            bits_per_frame (int):
                Number of bits per communication frame

            frame_duration (float):
                Duration of a single communication frame in seconds

            frame_errors (np.ndarray):
                Frame error indicators
        """

        num_frames = len(frame_errors)
        num_correct_frames = np.sum(np.invert(frame_errors))

        throughput = num_correct_frames * bits_per_frame / (num_frames * frame_duration)
        EvaluationTemplate.__init__(self, throughput)

    @property
    def title(self) -> str:
        return "Data Throughput"

    def artifact(self) -> ThroughputArtifact:
        return ThroughputArtifact(self.evaluation)


class ThroughputEvaluator(CommunicationEvaluator, Serializable):
    """Evaluate data throughput between two modems exchanging information."""

    yaml_tag = "ThroughputEvaluator"
    """YAML serialization tag"""

    __framer_error_evaluator: FrameErrorEvaluator

    def __init__(
        self,
        transmitting_modem: TransmittingModem,
        receiving_modem: ReceivingModem,
        plot_surface: bool = True,
    ) -> None:
        """
        Args:

            transmitting_modem (TransmittingModem):
                Modem transmitting information.

            receiving_modem (ReceivingModem):
                Modem receiving information.

            plot_surface (bool, optional):
                Plot the surface of the evaluation result in two-dimensional grids.
                Defaults to True.
        """

        # Initialize base class
        CommunicationEvaluator.__init__(self, transmitting_modem, receiving_modem, plot_surface)

        # Initialize class attributes
        self.__framer_error_evaluator = FrameErrorEvaluator(transmitting_modem, receiving_modem)

    def evaluate(self) -> ThroughputEvaluation:
        # Get the frame errors
        frame_errors = self.__framer_error_evaluator.evaluate().evaluation.flatten()

        # Transform frame errors to data throughput
        bits_per_frame = self.receiving_modem.num_data_bits_per_frame
        frame_duration = self.receiving_modem.frame_duration

        return ThroughputEvaluation(bits_per_frame, frame_duration, frame_errors)

    @property
    def title(self) -> str:
        return "Data Throughput"

    @property
    def abbreviation(self) -> str:
        return "DRX"