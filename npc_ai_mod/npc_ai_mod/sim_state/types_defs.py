"""Hashable tuple types for world activity and partner cohort fingerprints."""

from __future__ import annotations

import typing

# Affordance-class multiset: sorted (class __name__, count) pairs from a sim's SI state.
ClassMultiset = typing.Tuple[typing.Tuple[str, int], ...]
SimFingerprintRow = typing.Tuple[int, ClassMultiset, ClassMultiset]
# Sorted (sim_id → sorted partner ids) wired to the viewer (SI graph + shared object cohort).
PartnerWireFingerprint = typing.Tuple[typing.Tuple[int, typing.Tuple[int, ...]], ...]
WorldFingerprint = typing.Tuple[
    typing.Optional[int],
    typing.Optional[int],
    typing.Tuple[SimFingerprintRow, ...],
    PartnerWireFingerprint,
]
