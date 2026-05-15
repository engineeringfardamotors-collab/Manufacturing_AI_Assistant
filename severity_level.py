from __future__ import annotations
from enum import Enum

class SeverityLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def rank(cls, level: str) -> int:
        order = {cls.INFO: 0, cls.WARNING: 1, cls.ERROR: 2, cls.CRITICAL: 3}
        return order.get(cls(level), 99)
