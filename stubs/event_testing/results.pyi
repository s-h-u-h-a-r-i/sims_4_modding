# Derived from EA decompiled source (EA/simulation/event_testing/results.py).
# EnqueueResult.__bool__ → bool(self.test_result and self.execute_result)

from typing import Optional, Any

class TestResult:
    result: bool
    tooltip: Any
    icon: Any
    influence_by_active_mood: bool

    TRUE: "TestResult"
    NONE: "TestResult"

    def __init__(self, result: bool, *, tooltip: Any = ..., icon: Any = ..., influence_by_active_mood: bool = ..., reason: str = ...) -> None: ...
    def __bool__(self) -> bool: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

    @property
    def reason(self) -> Optional[str]: ...


class ExecuteResult:
    result: bool
    interaction: Any
    reason: Any

    NONE: "ExecuteResult"

    def __new__(cls, result: bool, interaction: Any, reason: Any) -> "ExecuteResult": ...
    def __bool__(self) -> bool: ...


class EnqueueResult:
    test_result: TestResult
    execute_result: ExecuteResult

    NONE: "EnqueueResult"

    def __new__(cls, test_result: Optional[TestResult] = ..., execute_result: Optional[ExecuteResult] = ...) -> "EnqueueResult": ...
    def __bool__(self) -> bool: ...

    @property
    def interaction(self) -> Any: ...
