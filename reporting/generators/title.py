"""
Title and summary slide generators.
"""

from typing import Dict, List, Optional
from ..core import DesignReviewGenerator


def add_title_slide(gen: DesignReviewGenerator,
                    subtitle: Optional[str] = None,
                    date: Optional[str] = None):
    """
    Add title slide to presentation.

    Args:
        gen: DesignReviewGenerator instance
        subtitle: Optional subtitle (e.g., "Preliminary Design Review")
        date: Optional date string
    """
    return gen.add_title_slide(subtitle=subtitle, date=date)


def add_summary_slide(gen: DesignReviewGenerator,
                      key_findings: List[str] = None,
                      recommendations: Optional[List[str]] = None,
                      next_steps: Optional[List[str]] = None,
                      compliance_result = None):
    """
    Add summary/conclusions slide.

    Task 10: Now supports compliance_result for dynamic compliance dashboard.

    Args:
        gen: DesignReviewGenerator instance
        key_findings: List of key findings (used if compliance_result not provided)
        recommendations: Optional list of recommendations
        next_steps: Optional list of next steps
        compliance_result: Optional ComplianceResult dataclass for dynamic dashboard
    """
    gen.add_section_slide("Summary & Conclusions")

    # Task 10: Generate compliance dashboard if result provided
    if compliance_result:
        _add_compliance_dashboard(gen, compliance_result)
    elif key_findings:
        # Legacy: use hardcoded findings
        gen.add_content_slide(
            "Key Findings",
            bullets=key_findings
        )

    # Recommendations if provided
    if recommendations:
        gen.add_content_slide(
            "Recommendations",
            bullets=recommendations
        )

    # Next steps if provided
    if next_steps:
        gen.add_content_slide(
            "Next Steps",
            bullets=next_steps
        )


def _add_compliance_dashboard(gen: DesignReviewGenerator, compliance_result):
    """
    Generate dynamic compliance dashboard (Task 10).

    Groups compliance checks by category and shows pass/fail statistics.

    Args:
        compliance_result: ComplianceResult dataclass instance
    """
    # Group checks by category
    categories = {}
    for check in compliance_result.checks:
        category = check.category
        if category not in categories:
            categories[category] = {'passed': 0, 'failed': 0, 'checks': []}
        if check.passed:
            categories[category]['passed'] += 1
        else:
            categories[category]['failed'] += 1
        categories[category]['checks'].append(check)

    # Build summary table data
    headers = ["Category", "Status", "Passed", "Total"]
    rows = []
    for cat_name, cat_data in categories.items():
        total = cat_data['passed'] + cat_data['failed']
        status = "PASS" if cat_data['failed'] == 0 else "FAIL"
        rows.append([cat_name, status, str(cat_data['passed']), str(total)])

    # Overall status
    total_passed = sum(c['passed'] for c in categories.values())
    total_failed = sum(c['failed'] for c in categories.values())
    total_checks = total_passed + total_failed
    overall_status = "ALL PASS" if total_failed == 0 else f"{total_failed} FAILURES"

    # Add dashboard slide
    gen.add_table_slide(
        f"Compliance Dashboard - {overall_status}",
        headers=headers,
        rows=rows
    )

    # Add findings based on compliance
    findings = []
    findings.append(f"Total compliance checks: {total_checks}")
    findings.append(f"Passed: {total_passed}, Failed: {total_failed}")

    if total_failed == 0:
        findings.append("All requirements met - ready for next phase")
    else:
        # List failed items
        findings.append("Failed requirements:")
        for cat_name, cat_data in categories.items():
            for check in cat_data['checks']:
                if not check.passed:
                    findings.append(f"   {check.requirement}: {check.actual:.2f} {check.units}")

    gen.add_content_slide("Compliance Summary", bullets=findings)
