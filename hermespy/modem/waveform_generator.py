# -*- coding: utf-8 -*-
"""
===========================
Communication Waveform Base
===========================
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from math import ceil, floor
from typing import Generic, Tuple, TYPE_CHECKING, Optional, Type, TypeVar, List

import numpy as np
from ruamel.yaml import SafeConstructor, SafeRepresenter, Node, ScalarNode

from hermespy.core import ChannelStateInformation, Serializable, Signal
from .symbols import Symbols

if TYPE_CHECKING:
    from hermespy.modem import Modem

__author__ = "Andre Noll Barreto"
__copyright__ = "Copyright 2022, Barkhausen Institut gGmbH"
__credits__ = ["Andre Noll Barreto", "Tobias Kronauer", "Jan Adler"]
__license__ = "AGPLv3"
__version__ = "0.3.0"
__maintainer__ = "Jan Adler"
__email__ = "jan.adler@barkhauseninstitut.org"
__status__ = "Prototype"


WaveformType = TypeVar('WaveformType', bound='WaveformGenerator')


class Synchronization(Generic[WaveformType], ABC, Serializable):
    """Abstract base class for synchronization routines of waveform generators.

    Refer to :footcite:t:`2016:nasir` for an overview of the current state of the art.
    """

    yaml_tag = u'Synchronization'
    """YAML serialization tag"""

    __waveform_generator: Optional[WaveformType]       # Waveform generator this routine is attached to

    def __init__(self,
                 waveform_generator: Optional[WaveformType] = None) -> None:
        """
        Args:
            waveform_generator (WaveformGenerator, optional):
                The waveform generator this synchronization routine is attached to.
        """

        self.__waveform_generator = waveform_generator

    @property
    def waveform_generator(self) -> Optional[WaveformType]:
        """Waveform generator this synchronization routine is attached to.

        Returns:
            Optional[WaveformType]:
                Handle to tghe waveform generator. None if the synchronization routine is floating.
        """

        return self.__waveform_generator

    @waveform_generator.setter
    def waveform_generator(self, value: Optional[WaveformType]) -> None:
        """Set waveform generator this synchronization routine is attached to."""

        # Un-register this synchronization routine from its previously assigned waveform
        if self.__waveform_generator is not None and self.__waveform_generator.synchronization is self:
            self.__waveform_generator.synchronization = Synchronization()

        self.__waveform_generator = value

    def synchronize(self,
                    signal: np.ndarray,
                    channel_state: ChannelStateInformation) -> List[Tuple[np.ndarray, ChannelStateInformation]]:
        """Simulates time-synchronization at the receiver-side.

        Sorts base-band signal-sections into frames in time-domain.

        Args:

            signal (np.ndarray):
                Vector of complex base-band samples of with `num_streams`x`num_samples` entries.

            channel_state (ChannelStateInformation):
                State of the wireless transmission channel over which `signal` has been propagated.

        Returns:
            List[Tuple[np.ndarray, ChannelStateInformation]]:
                Tuple of `signal` samples and channel transformations sorted into frames

        Raises:

            ValueError:
                If the number of received streams in `channel_state` does not equal one.
                If the length of `signal` and the number of samples in `channel_state` are not identical.

            RuntimeError:
                If the synchronization routine is floating
        """
        
        # Expand signal dimensionalty if input is flat
        if signal.ndim == 1:
            signal = signal[np.newaxis, :]

        if self.__waveform_generator is None:
            raise RuntimeError("Trying to synchronize with a floating synchronization routine")

        if signal.shape[1] != channel_state.num_samples + channel_state.num_delay_taps - 1:
            raise ValueError("Base-band signal and channel state contain a different amount of samples")

        samples_per_frame = self.__waveform_generator.samples_in_frame
        num_frames = int(floor(signal.shape[1] / samples_per_frame))

        # Slice signals and channel state information into frame-sized portions
        # Default synchronization does NOT account for possible delays,
        # i.e. assume the the first base-band signal's sample to also be the first frame's initial sample
        synchronized_frames: List[Tuple[np.ndarray, ChannelStateInformation]] = []
        for frame_idx in range(num_frames):

            frame_samples = signal[:, frame_idx*samples_per_frame:(1+frame_idx)*samples_per_frame]
            frame_channel_state = channel_state[:, :,  frame_idx*samples_per_frame:(1+frame_idx)*samples_per_frame, :]
            synchronized_frames.append((frame_samples, frame_channel_state))

        return synchronized_frames

    @classmethod
    def to_yaml(cls: Type[Synchronization], representer: SafeRepresenter, node: Synchronization) -> Node:
        """Serialize an `Synchronization` object to YAML.

        Args:
            representer (Synchronization):
                A handle to a representer used to generate valid YAML code.
                The representer gets passed down the serialization tree to each node.

            node (Synchronization):
                The `Synchronization` instance to be serialized.

        Returns:
            Node:
                The serialized YAML node
        """

        return representer.represent_scalar(cls.yaml_tag, None)

    @classmethod
    def from_yaml(cls: Type[Synchronization], constructor: SafeConstructor, node: Node) -> Synchronization:
        """Recall a new `Synchronization` instance from YAML.

        Args:
            constructor (SafeConstructor):
                A handle to the constructor extracting the YAML information.

            node (Node):
                YAML node representing the `Synchronization` serialization.

        Returns:
            Synchronization:
                Newly created `Synchronization` instance.
        """

        # For scalar nodes, initialize the synchronization routine with default parameters
        if isinstance(node, ScalarNode):
            return cls()

        return cls.InitializationWrapper(constructor.construct_mapping(node))


class ChannelEstimation(Generic[WaveformType], ABC):
    """Abstract base class for channel estimation routines of waveform generators."""

    def __init__(self,
                 waveform_generator: Optional[WaveformType] = None) -> None:
        """
        Args:
            waveform_generator (WaveformGenerator, optional):
                The waveform generator this estimation routine is attached to.
        """

        self.__waveform_generator = waveform_generator

    @property
    def waveform_generator(self) -> Optional[WaveformType]:
        """Waveform generator this synchronization routine is attached to.

        Returns:
            Optional[WaveformType]:
                Handle to the waveform generator. None if the synchronization routine is floating.
        """

        return self.__waveform_generator

    @waveform_generator.setter
    def waveform_generator(self, value: Optional[WaveformType]) -> None:
        """Set waveform generator this synchronization routine is attached to."""

        if self.__waveform_generator is not None:
            raise RuntimeError("Error trying to re-attach already attached synchronization routine.")

        self.__waveform_generator = value

    def estimate_channel(self,
                         signal: Signal,
                         csi: Optional[ChannelStateInformation] = None) -> ChannelStateInformation:
        """Estimate the wireless channel of a received communication frame.

        Args:

            signal (Signal):
                Signal model of the communication frame waveform.

            csi (ChannelStateInformation, optional):
                Ideal channel state information.
                May be required for some routines.

        Raises:
            ValueError:
                If `csi` is required but not provided.
        """

        if csi is None:
            raise ValueError("Ideal channel estimation requires prior channel state information")

        return csi
    

class ChannelEqualization(Generic[WaveformType], ABC):
    """Abstract base class for channel equalization routines of waveform generators."""

    def __init__(self,
                 waveform_generator: Optional[WaveformType] = None) -> None:
        """
        Args:
            waveform_generator (WaveformGenerator, optional):
                The waveform generator this equalization routine is attached to.
        """

        self.__waveform_generator = waveform_generator

    @property
    def waveform_generator(self) -> Optional[WaveformType]:
        """Waveform generator this equalization routine is attached to.

        Returns:
            Optional[WaveformType]:
                Handle to the waveform generator. None if the equalization routine is floating.
        """

        return self.__waveform_generator

    @waveform_generator.setter
    def waveform_generator(self, value: Optional[WaveformType]) -> None:
        """Set waveform generator this equalization routine is attached to."""

        if self.__waveform_generator is not None:
            raise RuntimeError("Error trying to re-attach already attached equalization routine.")

        self.__waveform_generator = value

    def equalize_channel(self,
                         signal: Signal,
                         csi: ChannelStateInformation,
                         snr: float = float('inf')) -> Signal:
        """Equalize the wireless channel of a received communication frame.

        Args:

            signal (Signal):
                Signal model of the communication frame waveform.

            csi (ChannelStateInformation):
                Channel state estimation

            snr (float):
                Assumed signal to noise ratio.
                May be required by some routines, infinite by default.

        Returns:
            Signal:
                The equalized signal model.
        """
        
        # The default routine performs no equalization
        return signal


class WaveformGenerator(ABC):
    """Implements an abstract waveform generator.

    Implementations for specific technologies should inherit from this class.
    """

    yaml_tag: str = "Waveform"
    """YAML serialization tag."""

    symbol_type: np.dtype = complex
    """Symbol type."""

    __modem: Optional[Modem]                        # Modem this waveform generator is attached to
    __synchronization: Synchronization              # Synchronization routine
    __channel_estimation: ChannelEstimation         # Channel estimation routine
    __channel_equalization: ChannelEqualization     # Channel equalization routine
    __oversampling_factor: int                      # Oversampling factor
    __modulation_order: int                         # Cardinality of the set of communication symbols

    def __init__(self,
                 modem: Optional[Modem] = None,
                 oversampling_factor: int = 1,
                 modulation_order: int = 16) -> None:
        """Waveform Generator initialization.

        Args:
            modem (Modem, optional):
                A modem this generator is attached to.
                By default, the generator is considered to be floating.

            oversampling_factor (int, optional):
                The factor at which the simulated baseband_signal is oversampled.

            modulation_order (int, optional):
                Order of modulation.
                Must be a non-negative power of two.
        """

        # Default parameters
        self.__modem = None
        self.oversampling_factor = oversampling_factor
        self.modulation_order = modulation_order
        self.synchronization = Synchronization(self)
        self.channel_estimation = ChannelEstimation(self)
        self.channel_equalization = ChannelEqualization(self)

        if modem is not None:
            self.modem = modem

        if oversampling_factor is not None:
            self.oversampling_factor = oversampling_factor

        if modulation_order is not None:
            self.modulation_order = modulation_order

    @property
    @abstractmethod
    def samples_in_frame(self) -> int:
        """The number of discrete samples per generated frame.

        Returns:
            int:
                The number of samples.
        """
        pass

    @property
    def oversampling_factor(self) -> int:
        """Access the oversampling factor.

        Returns:
            int:
                The oversampling factor.
        """

        return self.__oversampling_factor

    @oversampling_factor.setter
    def oversampling_factor(self, factor: int) -> None:
        """Modify the oversampling factor.

        Args:
            factor (int):
                The new oversampling factor.

        Raises:
            ValueError:
                If the oversampling `factor` is less than one.
        """

        if factor < 1:
            raise ValueError("The oversampling factor must be greater or equal to one")

        self.__oversampling_factor = factor

    @property
    def modulation_order(self) -> int:
        """Access the modulation order.

        Returns:
            int:
                The modulation order.
        """

        return self.__modulation_order

    @modulation_order.setter
    def modulation_order(self, order: int) -> None:
        """Modify the modulation order.

        Must be a positive power of two.

        Args:
            order (int):
                The new modulation order.

        Raises:
            ValueError:
                If `order` is not a positive power of two.
        """

        if order <= 0 or (order & (order - 1)) != 0:
            raise ValueError("Modulation order must be a positive power of two")

        self.__modulation_order = order

    @property
    def bits_per_symbol(self) -> int:
        """Number of bits transmitted per modulated symbol.

        Returns:
            int: Number of bits per symbol
        """

        return int(np.log2(self.modulation_order))

    @property
    @abstractmethod
    def bits_per_frame(self) -> int:
        """Number of bits required to generate a single data frame.

        Returns:
            int: Number of bits
        """
        ...

    @property
    @abstractmethod
    def symbols_per_frame(self) -> int:
        """Number of dat symbols per transmitted frame.

        Returns:
            int: Number of data symbols
        """
        ...

    @property
    def frame_duration(self) -> float:
        """Length of one data frame in seconds.

        Returns:
            float: Frame length in seconds.
        """

        return self.samples_in_frame / self.sampling_rate

    @property
    @abstractmethod
    def bit_energy(self) -> float:
        """Returns the theoretical average (discrete-time) bit energy of the modulated baseband_signal.

        Energy of baseband_signal x[k] is defined as \\sum{|x[k]}^2
        Only data bits are considered, i.e., reference, guard intervals are ignored.
        """
        ...

    @property
    @abstractmethod
    def symbol_energy(self) -> float:
        """The theoretical average symbol (discrete-time) energy of the modulated baseband_signal.

        Energy of baseband_signal x[k] is defined as \\sum{|x[k]}^2
        Only data bits are considered, i.e., reference, guard intervals are ignored.

        Returns:
            The average symbol energy in UNIT.
        """
        ...

    @property
    @abstractmethod
    def power(self) -> float:
        """Returns the theoretical average symbol (unitless) power,

        Power of baseband_signal x[k] is defined as \\sum_{k=1}^N{|x[k]|}^2 / N
        Power is the average power of the data part of the transmitted frame, i.e., bit energy x raw bit rate
        """
        ...

    @abstractmethod
    def map(self, data_bits: np.ndarray) -> Symbols:
        """Map a stream of bits to data symbols.

        Args:
            data_bits (np.ndarray):
                Vector containing a sequence of L hard data bits to be mapped onto data symbols.

        Returns:
            Symbols: Mapped data symbols.
        """
        ...

    @abstractmethod
    def unmap(self, symbols: Symbols) -> np.ndarray:
        """Map a stream of data symbols to data bits.

        Args:
            symbols (Symbols):
                Sequence of K data symbols to be mapped onto bit sequences.

        Returns:
            np.ndarray:
                Vector containing the resulting sequence of L data bits
                In general, L is greater or equal to K.
        """
        ...

    @abstractmethod
    def modulate(self, data_symbols: Symbols) -> Signal:
        """Modulate a stream of data symbols to a base-band signal containing a single data frame.

        Args:

            data_symbols (Symbols):
                Singular stream of data symbols to be modulated by this waveform.

        Returns:
            Signal: Signal model of a single modulate data frame.
        """
        ...

    # Hint: Channel propagation occurs here

    @abstractmethod
    def demodulate(self,
                   signal: np.ndarray,
                   channel_state: ChannelStateInformation,
                   noise_variance: float) -> Tuple[Symbols, ChannelStateInformation, np.ndarray]:
        """Demodulate a base-band signal stream to data symbols.

        Args:

            signal (np.ndarray):
                Vector of complex-valued base-band samples of a single communication frame.

            channel_state (ChannelStateInformation):
                Channel state information of a single communication frame.

            noise_variance (float):
                Variance of the thermal noise introduced during reception.

        Returns:
            (np.ndarray, ChannelStateInformation, np.ndarray):
                Tuple of 3 vectors of equal-length first dimension `num_symbols`.
                The demodulated data symbols, their channel estimates and their noise variance.
        """
        ...

    @property
    @abstractmethod
    def bandwidth(self) -> float:
        """Bandwidth of the frame generated by this generator.

        Used to estimate the minimal sampling frequency required to adequately simulate the scenario.

        Returns:
            float: Bandwidth in Hz.
        """
        ...
        
    @property
    def data_rate(self) -> float:
        """Data rate theoretically achieved by this waveform configuration.
        
        Returns:
        
            Bits per second.
        """
        
        time = self.frame_duration # ToDo: Consider guard interval
        bits = self.bits_per_frame
        
        return bits / time

    @property
    def modem(self) -> Modem:
        """Access the modem this generator is attached to.

        Returns:
            Modem:
                A handle to the modem.

        Raises:
            RuntimeError:
                If this waveform generator is not attached to a modem.
        """

        if self.__modem is None:
            raise RuntimeError("This waveform generator is not attached to any modem")

        return self.__modem

    @modem.setter
    def modem(self, handle: Modem) -> None:
        """Modify the modem this generator is attached to.

        Args:
            handle (Modem):
                Handle to a modem.

        Raises:
            RuntimeError:
                If the `modem` does not reference this generator.
        """

        if handle.waveform_generator is not self:
            handle.waveform_generator = self

        self.__modem = handle
        
    @property
    def synchronization(self) -> Synchronization:
        """Synchronization routine.

        Returns:
            Synchronization: Handle to the synchronization routine.
        """

        return self.__synchronization

    @synchronization.setter
    def synchronization(self, value: Synchronization) -> None:

        self.__synchronization = value

        if value.waveform_generator is not self:
            value.waveform_generator = self

    @property
    def channel_estimation(self) -> ChannelEstimation:
        """Channel estimation routine.

        Returns:
            ChannelEstimation: Handle to the synchronization routine.
        """

        return self.__channel_estimation

    @channel_estimation.setter
    def channel_estimation(self, value: ChannelEstimation) -> None:

        self.__channel_estimation = value

        if value.waveform_generator is not self:
            value.waveform_generator = self
            
    @property
    def channel_equalization(self) -> ChannelEqualization:
        """Channel estimation routine.

        Returns:
            ChannelEqualization: Handle to the equalization routine.
        """

        return self.__channel_equalization

    @channel_equalization.setter
    def channel_equalization(self, value: ChannelEqualization) -> None:

        self.__channel_equalization = value

        if value.waveform_generator is not self:
            value.waveform_generator = self

    @property
    @abstractmethod
    def sampling_rate(self) -> float:
        """Rate at which the waveform generator signal is internally sampled.

        Returns:
            float: Sampling rate in Hz.
        """
        ...

    @classmethod
    def to_yaml(cls: Type[WaveformGenerator], representer: SafeRepresenter, node: WaveformGenerator) -> Node:
        """Serialize an `WaveformGenerator` object to YAML.

        Args:
            representer (SafeRepresenter):
                A handle to a representer used to generate valid YAML code.
                The representer gets passed down the serialization tree to each node.

            node (WaveformGenerator):
                The `WaveformGenerator` instance to be serialized.

        Returns:
            Node:
                The serialized YAML node
        """

        state = {
            "oversampling_factor": node.__oversampling_factor,
            "modulation_order": node.modulation_order,
            'synchronization': node.synchronization,
        }

        return representer.represent_mapping(cls.yaml_tag, state)

    @classmethod
    def from_yaml(cls: Type[WaveformGenerator], constructor: SafeConstructor, node: Node) -> WaveformGenerator:
        """Recall a new `WaveformGenerator` instance from YAML.

        Args:
            constructor (SafeConstructor):
                A handle to the constructor extracting the YAML information.

            node (Node):
                YAML node representing the `WaveformGenerator` serialization.

        Returns:
            WaveformGenerator:
                Newly created `WaveformGenerator` instance.
        """

        return cls.InitializationWrapper(constructor.construct_mapping(node))


class PilotWaveformGenerator(WaveformGenerator, ABC):
    """Abstract base class of communication waveform generators generating a pilot signal."""

    @property
    @abstractmethod
    def pilot_signal(self) -> Signal:
        """Model of the pilot sequence within this communication waveform.

        Returns:
            Signal: The pilot sequence.
        """
        ...


class PilotSymbolSequence(ABC):
    """Abstract base class for pilot sequences."""

    @property
    @abstractmethod
    def sequence(self) -> np.ndarray:
        """The scalar sequence of pilot symbols.

        For a configurable pilot section, this symbol sequence will be repeated accordingly.

        Returns:
            The symbol sequence.
        """
        ...


class UniformPilotSymbolSequence(PilotSymbolSequence):
    """A pilot symbol sequence containing identical symbols.

    Only viable for testing purposes, since it makes the pilot sections easy to spot within the frame.
    Not advisable to be used in production scenarios.
    """

    __pilot_symbol: complex     # The configured pilot symbol

    def __init__(self, pilot_symbol: complex = 1. + 0.j) -> None:
        """
        Args:

            pilot_symbol (complex):
                The configured single pilot symbol.
                `1.` by default.
        """

        self.__pilot_symbol = pilot_symbol

    @property
    def sequence(self) -> np.ndarray:

        return np.array([self.__pilot_symbol], dtype=complex)


class CustomPilotSymbolSequence(PilotSymbolSequence):
    """A customized pilot symbol sequence.

    The user may freely chose the pilot symbols from samples within the complex plane.
    """

    __pilot_symbols: complex     # The configured pilot symbols

    def __init__(self, pilot_symbols: np.ndarray) -> None:
        """
        Args:

            pilot_symbols (np.ndarray):
                The configured pilot symbols
        """

        self.__pilot_symbols = pilot_symbols

    @property
    def sequence(self) -> np.ndarray:

        return self.__pilot_symbols


class ConfigurablePilotWaveform(PilotWaveformGenerator, ABC):
     
    pilot_symbol_sequence: PilotSymbolSequence
    """The configured pilot symbol sequence."""

    repeat_pilot_symbol_sequence: bool
    """Allow the repetition of pilot symbol sequences."""

    def __init__(self,
                 symbol_sequence: Optional[PilotSymbolSequence] = None,
                 repeat_symbol_sequence: bool = True) -> None:
        """
         Args:

            symbol_sequence (Optional[PilotSymbolSequence], optional):
                The configured pilot symbol sequence.
                Uniform by default.

            repeat_symbol_sequence (bool, optional):
                Allow the repetition of pilot symbol sequences.
                Enabled by default.
        """

        self.pilot_symbol_sequence = UniformPilotSymbolSequence() if symbol_sequence is None else symbol_sequence
        self.repeat_pilot_symbol_sequence = repeat_symbol_sequence

    def pilot_symbols(self, num_symbols: int) -> np.ndarray:
        """Sample a pilot symbol sequence.

        Args:
            num_symbols (int):
                The expected number of symbols within the sequence.

        Returns:
            A pilot symbol sequence of length `num_symbols`.

        Raises:

            RuntimeError:
                If a repetition of the symbol sequence is required but not allowed.
        """

        symbol_sequence = self.pilot_symbol_sequence.sequence
        num_repetitions = int(ceil(num_symbols / len(symbol_sequence)))

        if num_repetitions > 1:

            if not self.repeat_pilot_symbol_sequence:
                raise RuntimeError("Pilot symbol repetition required for sequence generation but not allowed")

            symbol_sequence = np.tile(symbol_sequence, num_repetitions)

        return symbol_sequence[:num_symbols]
