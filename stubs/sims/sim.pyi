from typing import Any, Optional

from event_testing.results import EnqueueResult
from interactions.context import InteractionContext
from interactions.interaction_queue import InteractionQueue
from interactions.si_state import SIState


class Sim:
    """Live in-world Sim object (returned by SimInfo.get_sim_instance())."""

    id: int
    si_state: SIState
    queue: Optional[InteractionQueue]

    def push_super_affordance(
        self,
        affordance: Any,
        target: Optional[Any],
        context: InteractionContext,
        *args: Any,
        **kwargs: Any,
    ) -> EnqueueResult: ...
