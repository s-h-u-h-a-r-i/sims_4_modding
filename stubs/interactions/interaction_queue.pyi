import typing
from collections.abc import Iterator

from interactions.base.super_interaction import SuperInteraction

class InteractionQueue:
    @property
    def running(self) -> typing.Optional[SuperInteraction]: ...
    def __iter__(self) -> Iterator[SuperInteraction]: ...
