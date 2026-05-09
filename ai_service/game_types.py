"""
Opt-in stubs for Sims 4 decompiled sources (EA/).

Run ./decompile_ea.sh once so EA/core and EA/simulation exist — same layout as npc_ai_mod.
Pyright resolves these via pyrightconfig.json executionEnvironments for ai_service.

Use this module when you prototype serializers that mirror EA types; do not import EA
packages at FastAPI startup for heavy work (keep HTTP handlers lightweight).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Examples — uncomment/use as needed when EA/ is populated:
    from sims.sim_info import SimInfo  # noqa: F401
    from sims4.log import Logger  # noqa: F401
