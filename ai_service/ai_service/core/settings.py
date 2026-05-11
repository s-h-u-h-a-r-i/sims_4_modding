from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeSettings(BaseSettings):
    """Uvicorn options for the local bridge. Env: ``NPC_AI_BRIDGE_*``."""

    model_config = SettingsConfigDict(
        env_prefix="NPC_AI_BRIDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8765, ge=1, le=65535)
    reload: bool = Field(default=False)
    ws_ping_interval: float | None = Field(
        default=None,
        description=(
            "If set, Uvicorn sends WebSocket ping frames this often. "
            "None disables (npc_ai_mod only reads the socket during each tick)."
        ),
    )
    ws_ping_timeout: float | None = Field(
        default=None,
        description="Seconds to wait for pong after a ping; use with ws_ping_interval.",
    )
