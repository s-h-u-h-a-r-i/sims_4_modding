from venues.venue_service import VenueService
from zone import Zone

from .director import director

_orig_venue_loading_finished = VenueService.on_loading_screen_animation_finished  # type: ignore[attr-defined]
_orig_zone_teardown = Zone.on_teardown


def _on_venue_loading_finished(self, *args, **kwargs):
    result = _orig_venue_loading_finished(self, *args, **kwargs)
    director.on_zone_loaded()
    return result


def _on_zone_teardown(self, *args, **kwargs):
    director.on_zone_unloaded()
    return _orig_zone_teardown(self, *args, **kwargs)


VenueService.on_loading_screen_animation_finished = _on_venue_loading_finished  # type: ignore[attr-defined]
Zone.on_teardown = _on_zone_teardown
