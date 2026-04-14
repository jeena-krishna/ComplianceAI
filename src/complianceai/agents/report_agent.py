"""Report Agent - Generates human-readable compliance reports."""

from typing import Dict, List, Any
import json
from datetime import datetime


class ReportAgent:
    """Agent responsible for generating compliance reports."""
    
    # Risk level thresholds
    RISK_THRESHOLDS = {
        'LOW': 0,      # No conflicts
        'MEDIUM': 1,   # 1-2 warnings
        'HIGH': 3,     # 3-5 moderate issues
        'CRITICAL': 6, # 6+ issues
    }
    
    # Alternative package suggestions for common problematic licenses
    PACKAGE_ALTERNATIVES = {
        'GPL-3.0': {
            '替代方案': 'Replace with MIT or Apache-2.0 licensed alternatives',
            'examples': {
                'requests': 'httpx (MIT)',
            }
        },
        'AGPL-3.0': {
            '替代方案': 'Replace with LGPL or permissive licensed alternatives',
            'examples': {}
        },
        'Proprietary': {
            '替代方案': 'Review license compatibility',
            'examples': {}
        },
    }
    
    def __init__(self):
        """Initialize the Report Agent."""
        pass
    
    def generate_report(self, licensed_dependencies: List[Dict[str, Any]], 
                         conflicts: List[Dict[str, Any]],
                         dependency_tree: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a compliance report based on dependencies and conflicts.
        
        Args:
            licensed_dependencies: List of dictionaries containing dependencies with license info
            conflicts: List of conflict dictionaries from ConflictAgent
            dependency_tree: Optional dependency tree from DependencyCrawler
            
        Returns:
            Dictionary containing the formatted report
        """
        # Determine overall risk level
        risk_level = self._calculate_risk_level(conflicts)
        
        # Count licenses by category
        license_counts = self._count_licenses(licensed_dependencies)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(conflicts, licensed_dependencies)
        
        # Build the report
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_version": "1.0.0",
            "summary": self._create_summary(
                licensed_dependencies, 
                conflicts, 
                risk_level,
                license_counts
            ),
            "findings": self._create_findings(licensed_dependencies, conflicts),
            "recommendations": recommendations,
            "dependencies": self._format_dependencies(licensed_dependencies),
            "dependency_tree": dependency_tree if dependency_tree else None,
        }
        
        return report
    
    def generate_text_report(self, licensed_dependencies: List[Dict[str, Any]], 
                             conflicts: List[Dict[str, Any]],
                             dependency_tree: Dict[str, Any] = None) -> str:
        """Generate a plain text compliance report.
        
        Args:
            licensed_dependencies: List of dictionaries containing dependencies with license info
            conflicts: List of conflict dictionaries
            dependency_tree: Optional dependency tree
            
        Returns:
            Plain text report string
        """
        report = self.generate_report(licensed_dependencies, conflicts, dependency_tree)
        
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("LICENSE COMPLIANCE REPORT")
        lines.append("=" * 70)
        lines.append(f"Generated: {report['timestamp']}")
        lines.append("")
        
        # Summary
        lines.append("-" * 70)
        lines.append("SUMMARY")
        lines.append("-" * 70)
        summary = report['summary']
        lines.append(f"Total Dependencies: {summary['total_dependencies']}")
        lines.append(f"Total Conflicts: {summary['total_conflicts']}")
        lines.append(f"  - Critical: {summary['critical_count']}")
        lines.append(f"  - Warnings: {summary['warning_count']}")
        lines.append(f"  - Info: {summary['info_count']}")
        lines.append(f"Overall Risk Level: {summary['risk_level']}")
        lines.append("")
        
        # License breakdown
        lines.append("License Breakdown:")
        for license_str, count in summary['license_counts'].items():
            lines.append(f"  - {license_str}: {count}")
        lines.append("")
        
        # Findings
        if report['findings']['conflicts']:
            lines.append("-" * 70)
            lines.append("FINDINGS")
            lines.append("-" * 70)
            
            for finding in report['findings']['conflicts']:
                severity = finding['severity'].upper()
                lines.append(f"[{severity}] {finding['description']}")
                
                if severity == 'CRITICAL':
                    lines.append(f"  Affected packages:")
                    for pkg in finding.get('affected_packages', []):
                        lines.append(f"    - {pkg}")
                elif severity == 'WARNING':
                    lines.append(f"  Affected packages:")
                    for pkg in finding.get('affected_packages', []):
                        lines.append(f"    - {pkg}")
                
                if finding.get('recommendation'):
                    lines.append(f"  Recommendation: {finding['recommendation']}")
                lines.append("")
        else:
            lines.append("No license conflicts detected.")
            lines.append("")
        
        # Unknown licenses
        if report['findings']['unknown_packages']:
            lines.append("-" * 70)
            lines.append("UNKNOWN LICENSES")
            lines.append("-" * 70)
            for pkg in report['findings']['unknown_packages']:
                lines.append(f"  - {pkg}")
            lines.append("")
        
        # Recommendations
        if report['recommendations']:
            lines.append("-" * 70)
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 70)
            
            for i, rec in enumerate(report['recommendations'], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        # Footer
        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_json_report(self, licensed_dependencies: List[Dict[str, Any]], 
                            conflicts: List[Dict[str, Any]],
                            dependency_tree: Dict[str, Any] = None) -> str:
        """Generate a JSON compliance report.
        
        Args:
            licensed_dependencies: List of dictionaries containing dependencies with license info
            conflicts: List of conflict dictionaries
            dependency_tree: Optional dependency tree
            
        Returns:
            JSON string
        """
        report = self.generate_report(licensed_dependencies, conflicts, dependency_tree)
        return json.dumps(report, indent=2)
    
    def _calculate_risk_level(self, conflicts: List[Dict[str, Any]]) -> str:
        """Calculate the overall risk level based on conflicts.
        
        Args:
            conflicts: List of conflict dictionaries
            
        Returns:
            Risk level: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
        """
        if not conflicts:
            return 'LOW'
        
        critical = sum(1 for c in conflicts if c.get('severity') == 'critical')
        warning = sum(1 for c in conflicts if c.get('severity') == 'warning')
        total = critical + warning
        
        if total >= self.RISK_THRESHOLDS['CRITICAL']:
            return 'CRITICAL'
        elif total >= self.RISK_THRESHOLDS['HIGH']:
            return 'HIGH'
        elif total >= self.RISK_THRESHOLDS['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _count_licenses(self, dependencies: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count dependencies by license type.
        
        Args:
            dependencies: List of dependencies with license info
            
        Returns:
            Dictionary mapping license to count
        """
        counts = {}
        for dep in dependencies:
            license = dep.get('license', 'Unknown')
            counts[license] = counts.get(license, 0) + 1
        return counts
    
    def _create_summary(self, dependencies: List[Dict[str, Any]], 
                       conflicts: List[Dict[str, Any]],
                       risk_level: str,
                       license_counts: Dict[str, int]) -> Dict[str, Any]:
        """Create the summary section of the report."""
        critical = sum(1 for c in conflicts if c.get('severity') == 'critical')
        warning = sum(1 for c in conflicts if c.get('severity') == 'warning')
        info = sum(1 for c in conflicts if c.get('severity') == 'info')
        
        return {
            "total_dependencies": len(dependencies),
            "total_conflicts": len(conflicts),
            "critical_count": critical,
            "warning_count": warning,
            "info_count": info,
            "risk_level": risk_level,
            "license_counts": license_counts,
        }
    
    def _create_findings(self, dependencies: List[Dict[str, Any]], 
                        conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create the findings section with detailed conflict information."""
        findings = []
        
        # Group conflicts by severity
        by_severity = {'critical': [], 'warning': [], 'info': []}
        for conflict in conflicts:
            severity = conflict.get('severity', 'info')
            by_severity[severity].append(conflict)
        
        # Format conflicts for report
        for severity in ['critical', 'warning', 'info']:
            for conflict in by_severity[severity]:
                packages = conflict.get('packages_1', []) + conflict.get('packages_2', [])
                if 'packages' in conflict:
                    packages = conflict.get('packages', [])
                
                findings.append({
                    "severity": severity.upper(),
                    "description": conflict.get('description', ''),
                    "affected_packages": list(set(packages)),
                    "recommendation": conflict.get('recommendation', ''),
                    "license_1": conflict.get('license_1', ''),
                    "license_2": conflict.get('license_2', ''),
                })
        
        # Find packages with unknown licenses
        unknown = [d.get('name') for d in dependencies 
                  if d.get('license') == 'Unknown' or not d.get('license')]
        
        return {
            "conflicts": findings,
            "unknown_packages": unknown,
            "total_unknown": len(unknown),
        }
    
    def _generate_recommendations(self, conflicts: List[Dict[str, Any]], 
                                  dependencies: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations based on conflicts."""
        recommendations = []
        
        # Process each conflict
        for conflict in conflicts:
            severity = conflict.get('severity', 'info')
            lic1 = conflict.get('license_1', '')
            lic2 = conflict.get('license_2', '')
            
            if severity == 'critical':
                recommendations.append(
                    f"CRITICAL: Resolve {lic1} vs {lic2} conflict - "
                    f"Consider replacing packages with permissive alternatives"
                )
            elif severity == 'warning':
                # Check for unknown licenses
                if 'Unknown' in [lic1, lic2]:
                    recommendations.append(
                        f"WARNING: Verify license for unknown packages - "
                        f"Manually check package repositories"
                    )
        
        # Check for specific problematic licenses
        license_counts = self._count_licenses(dependencies)
        
        if 'AGPL-3.0' in license_counts:
            count = license_counts['AGPL-3.0']
            recommendations.append(
                f"WARNING: {count} package(s) use AGPL-3.0 - "
                f"This license requires source code to be shared even for web services"
            )
        
        if 'GPL-3.0' in license_counts:
            count = license_counts['GPL-3.0']
            recommendations.append(
                f"INFO: {count} package(s) use GPL-3.0 - "
                f"This is copyleft; consider if proprietary linking is acceptable"
            )
        
        # General recommendation if no issues
        if not recommendations:
            recommendations.append(
                "All dependencies are license compatible - No action required"
            )
        
        return recommendations
    
    def _format_dependencies(self, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format dependencies for the report."""
        return [
            {
                "name": d.get('name'),
                "version": d.get('version'),
                "license": d.get('license', 'Unknown'),
                "license_source": d.get('license_source', 'unknown'),
            }
            for d in dependencies
        ]