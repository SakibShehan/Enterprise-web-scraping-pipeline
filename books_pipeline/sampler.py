import random
from typing import Callable, Hashable, List, Optional, TypeVar

T = TypeVar("T")


class RandomSampler:
    """Pick random distinct items with an optional repeatable seed."""

    def __init__(self, seed: Optional[str] = None):
        """Create the sampler; a seed makes results repeatable."""
        self.rng = random.Random(seed)

    def sample(
        self,
        items: List[T],
        size: int,
        key: Optional[Callable[[T], Hashable]] = None,
    ) -> List[T]:
        """Return up to size distinct items, or all of them if fewer exist."""
        key = key or (lambda item: item)
        unique = list({key(item): item for item in items}.values())
        return self.rng.sample(unique, min(size, len(unique)))