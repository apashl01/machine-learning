"""
Compliance Matrix slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
from ..core import DesignReviewGenerator


def add_compliance_slides(gen: DesignReviewGenerator,
                          compliance_result = None,
                          table_rows: Optional[List[Dict]] = None):
    """
    Add Compliance Matrix slides.

    Args:
        gen: DesignReviewGenerator instance
        compliance_result: ComplianceResult object
        table_rows: List of dicts for table display
    """
    gen.add_section_slide("Requirements Compliance",
                          "Pass/Fail Matrix")

    if compliance_result is None:
        gen.add_content_slide(
            "Compliance Status",
            bullets=["Compliance data not available"]
        )
        return

    # Summary slide
    status = "COMPLIANT" if compliance_result.is_compliant else "NON-COMPLIANT"
    summary_bullets = [
        f"Overall Status: {status}",
        f"Requirements Passed: {compliance_result.passed_checks}/{compliance_result.total_checks}",
        f"Compliance Rate: {compliance_result.compliance_rate:.0f}%",
    ]

    if compliance_result.failed_checks > 0:
        failed = [c for c in compliance_result.checks if not c.passed]
        summary_bullets.append("")
        summary_bullets.append("Failed Requirements:")
        for check in failed:
            summary_bullets.append(f"  - {check.name}: {check.actual:.2f} vs {check.threshold:.2f} {check.units}")

    gen.add_content_slide(
        "Compliance Summary",
        bullets=summary_bullets
    )

    # Compliance table by category
    if table_rows:
        categories = sorted(set(row['category'] for row in table_rows))

        for cat in categories:
            cat_rows = [r for r in table_rows if r['category'] == cat]

            headers = ["Requirement", "Threshold", "Actual", "Status"]
            rows = []
            for r in cat_rows:
                rows.append([
                    r['requirement'],
                    r['threshold'],
                    r['actual'],
                    r['status']
                ])

            gen.add_table_slide(f"Compliance: {cat}", headers, rows)
