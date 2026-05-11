"""Distributor operation types (subset for modding)."""

from __future__ import annotations

from typing import List, Tuple, Union

__all__ = ("Op", "TravelBringToZone")

SummonInfoWire = Union[Tuple[int, int, int, int], List[int]]

class Op: ...

class TravelBringToZone(Op):
    summon_info: List[int]

    def __init__(self, summon_info: SummonInfoWire) -> None: ...
