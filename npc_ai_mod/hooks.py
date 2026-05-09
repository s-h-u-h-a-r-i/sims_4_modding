from typing import TYPE_CHECKING

from venues.venue_service import VenueService

from . import director

if TYPE_CHECKING:
    pass

_orig_venue_loading_finished = VenueService.on_loading_screen_animation_finished  # type: ignore[attr-defined]


def _on_venue_loading_finished(self, *args, **kwargs):
    result = _orig_venue_loading_finished(self, *args, **kwargs)
    director.on_zone_loaded()
    return result


VenueService.on_loading_screen_animation_finished = _on_venue_loading_finished  # type: ignore[attr-defined]
