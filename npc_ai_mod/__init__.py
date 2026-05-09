"""
npc_ai_mod — entry point.

Imported by the game on startup. Registers all game hooks so the rest of
the mod activates at the right moment (after a save finishes loading).
"""
from npc_ai_mod import hooks  # noqa: F401
