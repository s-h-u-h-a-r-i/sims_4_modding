import enum
from typing import Any, Optional


class InteractionSource(enum.IntEnum):
    PIE_MENU = 0
    AUTONOMY = 1
    BODY_CANCEL_AOP = 2
    CARRY_CANCEL_AOP = 3
    SCRIPT = 4
    UNIT_TEST = 5
    POSTURE_GRAPH = 6
    SOCIAL_ADJUSTMENT = 7
    REACTION = 8
    GET_COMFORTABLE = 9
    SCRIPT_WITH_USER_INTENT = 10
    VEHCILE_CANCEL_AOP = 11


class QueueInsertStrategy(enum.IntEnum):
    LAST = 0
    NEXT = 1
    FIRST = 2


class InteractionContext:
    SOURCE_PIE_MENU: InteractionSource
    SOURCE_AUTONOMY: InteractionSource
    SOURCE_BODY_CANCEL_AOP: InteractionSource
    SOURCE_CARRY_CANCEL_AOP: InteractionSource
    SOURCE_SCRIPT: InteractionSource

    def __init__(
        self,
        sim: Any,
        source: InteractionSource,
        priority: Any,
        *,
        insert_strategy: QueueInsertStrategy = ...,
        run_priority: Any = ...,
        client: Any = ...,
        pick: Any = ...,
        **kwargs: Any,
    ) -> None: ...
