from typing import Any, Iterator, Optional


class InteractionQueue:
    @property
    def running(self) -> Any: ...

    def __iter__(self) -> Iterator[Any]: ...
