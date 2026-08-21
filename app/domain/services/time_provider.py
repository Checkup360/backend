from abc import ABC, abstractmethod
from datetime import date, datetime


class TimeProvider(ABC):
    @abstractmethod
    def utcnow(self) -> datetime:
        pass

    @abstractmethod
    def today(self) -> date:
        pass
