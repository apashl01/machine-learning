"""
System Requirements Compliance Checker

Loads requirements from requirements.yaml and checks calculated
performance against them to generate a Pass/Fail compliance matrix.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml


@dataclass
class RequirementCheck:
    """Result of a single requirement check."""
    name: str
    category: str
    requirement: str          # Description of requirement
    threshold: float          # Required value
    actual: float             # Measured/calculated value
    units: str
    passed: bool
    margin_db: Optional[float] = None  # Margin (positive = passing)

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        margin_str = f" (margin: {self.margin_db:+.1f} dB)" if self.margin_db else ""
        return f"[{status}] {self.name}: {self.actual:.2f} {self.units} (req: {self.threshold:.2f}){margin_str}"


@dataclass
class ComplianceResult:
    """Complete compliance check results."""
    checks: List[RequirementCheck] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_checks(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def compliance_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.passed_checks / self.total_checks * 100

    @property
    def is_compliant(self) -> bool:
        return self.failed_checks == 0

    def get_by_category(self, category: str) -> List[RequirementCheck]:
        return [c for c in self.checks if c.category == category]

    def print_summary(self):
        """Print compliance summary."""
        print("\n" + "="*70)
        print("REQUIREMENTS COMPLIANCE MATRIX")
        print("="*70)

        categories = sorted(set(c.category for c in self.checks))

        for cat in categories:
            cat_checks = self.get_by_category(cat)
            cat_passed = sum(1 for c in cat_checks if c.passed)
            print(f"\n{cat.upper()} ({cat_passed}/{len(cat_checks)} passed)")
            print("-" * 50)
            for check in cat_checks:
                print(f"  {check}")

        print("\n" + "="*70)
        status = "COMPLIANT" if self.is_compliant else "NON-COMPLIANT"
        print(f"OVERALL: {status} - {self.passed_checks}/{self.total_checks} requirements met ({self.compliance_rate:.0f}%)")
        print("="*70)


def load_requirements(path: Optional[str] = None) -> Dict:
    """Load requirements from YAML file (Task 1.0: Updated to config/ directory)."""
    if path is None:
        path = Path(__file__).parent.parent / "config" / "requirements.yaml"
    else:
        path = Path(path)

    with open(path, 'r') as f:
        return yaml.safe_load(f)


def check_compliance(
    performance: Dict,
    requirements: Optional[Dict] = None
) -> ComplianceResult:
    """
    Check system performance against requirements.

    Args:
        performance: Dict of calculated performance metrics
        requirements: Requirements dict (loads from YAML if None)

    Returns:
        ComplianceResult with all checks
    """
    if requirements is None:
        requirements = load_requirements()

    result = ComplianceResult()

    # Detection requirements
    if 'detection' in requirements:
        det_req = requirements['detection']

        # Sensitivity checks
        if 'sensitivity_dbm' in det_req and 'sensitivity' in performance:
            for band, req_val in det_req['sensitivity_dbm'].items():
                if band in performance['sensitivity']:
                    actual = performance['sensitivity'][band]
                    passed = actual <= req_val  # Lower is better for sensitivity
                    margin = req_val - actual
                    result.checks.append(RequirementCheck(
                        name=f"Sensitivity ({band})",
                        category="Detection",
                        requirement=f"Sensitivity <= {req_val} dBm",
                        threshold=req_val,
                        actual=actual,
                        units="dBm",
                        passed=passed,
                        margin_db=margin
                    ))

        # Detection range
        if 'detection_range_km' in det_req and 'detection_range_km' in performance:
            req_min = det_req['detection_range_km'].get('min', 0)
            actual = performance['detection_range_km']
            passed = actual >= req_min
            result.checks.append(RequirementCheck(
                name="Detection Range",
                category="Detection",
                requirement=f"Range >= {req_min} km",
                threshold=req_min,
                actual=actual,
                units="km",
                passed=passed
            ))

    # Measurement accuracy requirements
    if 'measurement' in requirements:
        meas_req = requirements['measurement']

        # AOA accuracy
        if 'aoa_accuracy_deg' in meas_req and 'aoa_accuracy_deg' in performance:
            req_val = meas_req['aoa_accuracy_deg']
            actual = performance['aoa_accuracy_deg']
            passed = actual <= req_val
            result.checks.append(RequirementCheck(
                name="AOA Accuracy",
                category="Measurement",
                requirement=f"AOA RMS <= {req_val} deg",
                threshold=req_val,
                actual=actual,
                units="deg",
                passed=passed
            ))

        # Frequency accuracy
        if 'frequency_accuracy_mhz' in meas_req and 'frequency_accuracy_mhz' in performance:
            req_val = meas_req['frequency_accuracy_mhz']
            actual = performance['frequency_accuracy_mhz']
            passed = actual <= req_val
            result.checks.append(RequirementCheck(
                name="Frequency Accuracy",
                category="Measurement",
                requirement=f"Freq RMS <= {req_val} MHz",
                threshold=req_val,
                actual=actual,
                units="MHz",
                passed=passed
            ))

    # Geolocation requirements
    if 'geolocation' in requirements:
        geo_req = requirements['geolocation']

        # CEP
        if 'cep_m' in geo_req and 'cep_m' in performance:
            req_val = geo_req['cep_m']
            actual = performance['cep_m']
            passed = actual <= req_val
            result.checks.append(RequirementCheck(
                name="Geolocation CEP",
                category="Geolocation",
                requirement=f"CEP <= {req_val} m",
                threshold=req_val,
                actual=actual,
                units="m",
                passed=passed
            ))

        # Valid measurement rate
        if 'min_valid_measurement_rate' in geo_req and 'valid_measurement_rate' in performance:
            req_val = geo_req['min_valid_measurement_rate'] * 100
            actual = performance['valid_measurement_rate'] * 100
            passed = actual >= req_val
            result.checks.append(RequirementCheck(
                name="Valid Measurement Rate",
                category="Geolocation",
                requirement=f"Rate >= {req_val:.0f}%",
                threshold=req_val,
                actual=actual,
                units="%",
                passed=passed
            ))

    # Dynamic range requirements
    if 'dynamic_range' in requirements:
        dr_req = requirements['dynamic_range']

        if 'instantaneous_db' in dr_req and 'dynamic_range_db' in performance:
            req_val = dr_req['instantaneous_db']
            actual = performance['dynamic_range_db']
            passed = actual >= req_val
            result.checks.append(RequirementCheck(
                name="Dynamic Range",
                category="Dynamic Range",
                requirement=f"DR >= {req_val} dB",
                threshold=req_val,
                actual=actual,
                units="dB",
                passed=passed
            ))

        if 'sfdr_db' in dr_req and 'sfdr_db' in performance:
            req_val = dr_req['sfdr_db']
            actual = performance['sfdr_db']
            passed = actual >= req_val
            result.checks.append(RequirementCheck(
                name="SFDR",
                category="Dynamic Range",
                requirement=f"SFDR >= {req_val} dB",
                threshold=req_val,
                actual=actual,
                units="dB",
                passed=passed
            ))

    # RF chain requirements (Task 9.3: Path-Specific)
    if 'rf_chain' in requirements:
        rf_req = requirements['rf_chain']

        # Check if we have path-specific performance data
        if 'all_paths' in performance:
            all_paths = performance['all_paths']

            # Iterate through each path category in requirements
            for category_name, category_req in rf_req.items():
                if not isinstance(category_req, dict):
                    continue  # Skip non-category entries

                # Get list of path IDs for this category
                req_path_ids = category_req.get('paths', [])

                # Check each path in performance data
                for path in all_paths:
                    path_id = path.get('id', '')
                    path_name = path.get('name', path_id)
                    path_type = path.get('type', 'RX')

                    # Match path to category
                    if path_id not in req_path_ids:
                        continue  # Not in this category

                    # Check noise figure (RX paths only)
                    if path_type == 'RX' and 'max_noise_figure_db' in category_req:
                        req_val = category_req['max_noise_figure_db']
                        actual = path.get('cascade_nf_db', 0)
                        passed = actual <= req_val
                        result.checks.append(RequirementCheck(
                            name=f"{path_name} NF",
                            category="RF Chain",
                            requirement=f"NF <= {req_val} dB",
                            threshold=req_val,
                            actual=actual,
                            units="dB",
                            passed=passed
                        ))

                    # Check gain (RX paths)
                    if path_type == 'RX' and 'min_gain_db' in category_req:
                        req_val = category_req['min_gain_db']
                        actual = path.get('total_gain_db', 0)
                        passed = actual >= req_val
                        result.checks.append(RequirementCheck(
                            name=f"{path_name} Gain",
                            category="RF Chain",
                            requirement=f"Gain >= {req_val} dB",
                            threshold=req_val,
                            actual=actual,
                            units="dB",
                            passed=passed
                        ))

                    # Check output power (TX paths)
                    if path_type == 'TX' and 'min_output_power_dbm' in category_req:
                        req_val = category_req['min_output_power_dbm']
                        actual = path.get('output_power_dbm', 0)
                        passed = actual >= req_val
                        result.checks.append(RequirementCheck(
                            name=f"{path_name} Output Power",
                            category="RF Chain",
                            requirement=f"Output >= {req_val} dBm",
                            threshold=req_val,
                            actual=actual,
                            units="dBm",
                            passed=passed
                        ))

                    # Check max gain (TX paths)
                    if path_type == 'TX' and 'max_gain_db' in category_req:
                        req_val = category_req['max_gain_db']
                        actual = path.get('total_gain_db', 0)
                        passed = actual <= req_val
                        result.checks.append(RequirementCheck(
                            name=f"{path_name} Max Gain",
                            category="RF Chain",
                            requirement=f"Gain <= {req_val} dB",
                            threshold=req_val,
                            actual=actual,
                            units="dB",
                            passed=passed
                        ))

        # Legacy single-path checks (backward compatibility)
        elif 'max_noise_figure_db' in rf_req and 'noise_figure_db' in performance:
            req_val = rf_req['max_noise_figure_db']
            actual = performance['noise_figure_db']
            passed = actual <= req_val
            result.checks.append(RequirementCheck(
                name="RF Chain NF",
                category="RF Chain",
                requirement=f"NF <= {req_val} dB",
                threshold=req_val,
                actual=actual,
                units="dB",
                passed=passed
            ))

        elif 'min_gain_db' in rf_req and 'rf_gain_db' in performance:
            req_val = rf_req['min_gain_db']
            actual = performance['rf_gain_db']
            passed = actual >= req_val
            result.checks.append(RequirementCheck(
                name="RF Chain Gain",
                category="RF Chain",
                requirement=f"Gain >= {req_val} dB",
                threshold=req_val,
                actual=actual,
                units="dB",
                passed=passed
            ))

    # Coverage requirements
    if 'coverage' in requirements:
        cov_req = requirements['coverage']

        if 'azimuth_coverage_deg' in cov_req and 'azimuth_coverage_deg' in performance:
            req_val = cov_req['azimuth_coverage_deg']
            actual = performance['azimuth_coverage_deg']
            passed = actual >= req_val
            result.checks.append(RequirementCheck(
                name="Azimuth Coverage",
                category="Coverage",
                requirement=f"Coverage >= {req_val} deg",
                threshold=req_val,
                actual=actual,
                units="deg",
                passed=passed
            ))

    return result


def generate_compliance_report(
    performance: Dict,
    requirements: Optional[Dict] = None
) -> Tuple[ComplianceResult, List[Dict]]:
    """
    Generate compliance report suitable for PowerPoint.

    Returns:
        Tuple of (ComplianceResult, list of dicts for table rows)
    """
    result = check_compliance(performance, requirements)

    # Format for PowerPoint table
    table_rows = []
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        table_rows.append({
            'requirement': check.name,
            'category': check.category,
            'threshold': f"{check.threshold:.2f} {check.units}",
            'actual': f"{check.actual:.2f} {check.units}",
            'status': status,
            'margin': f"{check.margin_db:+.1f} dB" if check.margin_db else "N/A"
        })

    return result, table_rows
