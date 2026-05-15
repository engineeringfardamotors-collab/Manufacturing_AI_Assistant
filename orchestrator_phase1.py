from models.phase1_result import Phase1Result
from models.severity_level import SeverityLevel


class OrchestratorPhase1:
    def summarize_issues(self, issues):
        critical_count = sum(1 for x in issues if x.severity == SeverityLevel.CRITICAL)
        error_count = sum(1 for x in issues if x.severity == SeverityLevel.ERROR)
        warning_count = sum(1 for x in issues if x.severity == SeverityLevel.WARNING)
        info_count = sum(1 for x in issues if x.severity == SeverityLevel.INFO)

        return Phase1Result(
            total_issues=len(issues),
            critical_issues=critical_count,
            error_issues=error_count,
            warning_issues=warning_count,
            info_issues=info_count,
            issues=issues,
        )