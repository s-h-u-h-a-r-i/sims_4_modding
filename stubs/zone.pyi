from venues.venue_service import VenueService

class Zone:
    venue_service: VenueService

    def on_teardown(self, *args: object, **kwargs: object) -> None: ...
