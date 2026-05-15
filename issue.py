from __future__ import annotations
from dataclasses import dataclass, field
from models.severity_level import SeverityLevel

@dataclass
class ValidationIssue:
    issue_code: str
    severity: SeverityLevel
    message: str
    part_number: str | None = None
    source_file: str | None = None
    sheet_name: str | None = None
    row_ref: str | int | None = None
    expected: str | float | int | None = None
    actual: str | float | int | None = None
    station: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "issue_code": self.issue_code,
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "message": self.message,
            "part_number": self.part_number,
            "source_file": self.source_file,
            "sheet_name": self.sheet_name,
            "row_ref": self.row_ref,
            "expected": self.expected,
            "actual": self.actual,
            "station": self.station,
            "extra": self.extra,
        }
