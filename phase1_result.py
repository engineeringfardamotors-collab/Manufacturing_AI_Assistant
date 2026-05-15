from dataclasses import dataclass, field
from typing import List

from models.issue import ValidationIssue


@dataclass
class Phase1Result:
    total_issues: int = 0
    critical_issues: int = 0
    error_issues: int = 0
    warning_issues: int = 0
    info_issues: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)