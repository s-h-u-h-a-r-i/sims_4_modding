"""Distributor singleton — queues ops to the game client."""

from __future__ import annotations

from distributor.ops import Op

__all__ = ("Distributor",)


class Distributor:
    @classmethod
    def instance(cls) -> Distributor: ...

    def add_op(self, obj: object, op: Op) -> None: ...

    def add_op_with_no_owner(self, op: Op) -> None: ...
