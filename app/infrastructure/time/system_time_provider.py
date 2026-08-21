from datetime import date, datetime, timezone

from app.domain.services.time_provider import TimeProvider


class SystemTimeProvider(TimeProvider):
    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    def today(self) -> date:
        return date.today()
