from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ("settings",)


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


settings = BridgeSettings()
