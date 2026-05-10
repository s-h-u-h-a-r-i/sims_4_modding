from ai_service.core.constants import STATIC_DIR

from .v1 import router as viewer_v1_router

__all__ = ("viewer_v1_router", "STATIC_DIR")
