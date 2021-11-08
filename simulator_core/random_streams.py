import os
import time
import csv

from numpy import random as rnd

__author__ = "André Noll Barreto"
__copyright__ = "Copyright 2021, Barkhausen Institut gGmbH"
__credits__ = ["André Barreto", "Jan Adler"]
__license__ = "AGPLv3"
__version__ = "0.1.0"
__maintainer__ = "André Noll Barreto"
__email__ = "andre.nollbarreto@barkhauseninstitut.org"
__status__ = "Prototype"


class RandomStreams:
    """Provides a framework for random number generation.

    Multiple random streams are created, which are independently used in different parts of the code.

    Attributes:
        seed_types(List[str]): types of random numbers to be created.
        seeds_file_name(str): mat file containing good seeds.
        seeds_dir_name(str): parent directory of seeds_file_name
    """
    seeds_dir_name = "simulator_core"
    seeds_file_name = "RandomNumberGeneratorSeeds.csv"
    seed_types = ['noise', 'channel', 'source', 'hardware']

    def __init__(self, seed: int) -> None:
        file_path = os.path.join(
            os.getcwd(),
            self.seeds_dir_name,
            self.seeds_file_name)
        with open(file_path, 'r') as f:
            r = csv.reader(f, delimiter=',')
            seed_set = [int(row[0]) for row in r]

        self._rng_dict = {}

        if seed < 0:
            # get random seed from clock
            seed = int((time.time() * 1000))

        for idx, seed_type in enumerate(self.seed_types):
            seed_index = (seed + idx) % len(seed_set)
            current_seed = seed_set[seed_index]
            self._rng_dict.update({seed_type: rnd.RandomState(current_seed)})

    def get_rng(self, seed_type: str) -> rnd.RandomState:
        """This method returns a previously instanced random number generator.

        Args:
            seed_type (str): The type to get the random number generator for.

        Returns:
            rnd.RandomState: Random number generator.
        """
        if seed_type not in self.seed_types:
            raise ValueError('ERROR in simulator_core:random_streams:get_rng() - ' +
                             'invalid seed type (' + seed_type + ')')
        return self._rng_dict[seed_type]
