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
                      key_findings: List[str],
                      recommendations: Optional[List[str]] = None,
                      next_steps: Optional[List[str]] = None):
    """
    Add summary/conclusions slide.

    Args:
        gen: DesignReviewGenerator instance
        key_findings: List of key findings
        recommendations: Optional list of recommendations
        next_steps: Optional list of next steps
    """
    gen.add_section_slide("Summary & Conclusions")

    # Key findings
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
