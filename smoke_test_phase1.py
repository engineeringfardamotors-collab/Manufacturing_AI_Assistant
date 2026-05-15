import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from models.issue import ValidationIssue
from models.severity_level import SeverityLevel
from services.engine.orchestrator_phase1 import OrchestratorPhase1

def run_smoke_test():
    issues = [
        ValidationIssue(issue_code="E001", severity=SeverityLevel.ERROR, message="Part missing"),
        ValidationIssue(issue_code="W001", severity=SeverityLevel.WARNING, message="Qty mismatch"),
        ValidationIssue(issue_code="C001", severity=SeverityLevel.CRITICAL, message="Duplicate key"),
        ValidationIssue(issue_code="I001", severity=SeverityLevel.INFO, message="Normalized value"),
    ]

    engine = OrchestratorPhase1()
    result = engine.summarize_issues(issues)

    print("TOTAL:", result.total_issues)
    print("CRITICAL:", result.critical_issues)
    print("ERROR:", result.error_issues)
    print("WARNING:", result.warning_issues)
    print("INFO:", result.info_issues)

if __name__ == "__main__":
    run_smoke_test()