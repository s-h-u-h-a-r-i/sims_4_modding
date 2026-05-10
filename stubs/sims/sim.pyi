from typing import Any, Optional

from interactions.context import InteractionContext


class Sim:
    """Live in-world Sim object (returned by SimInfo.get_sim_instance())."""

    def push_super_affordance(
        self,
        affordance: Any,
        target: Optional[Any],
        context: InteractionContext,
        *args: Any,
        **kwargs: Any,
    ) -> bool: ...
