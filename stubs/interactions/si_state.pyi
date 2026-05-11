from collections.abc import Iterator

from interactions.base.super_interaction import SuperInteraction


class SIState:
    def sis_actor_gen(self) -> Iterator[SuperInteraction]: ...
