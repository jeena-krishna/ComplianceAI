"""Orchestrator module that coordinates between different AI agents."""

from typing import Dict, Any
from .agents.dependency_agent import DependencyAgent
from .agents.license_agent import LicenseAgent
from .agents.conflict_agent import ConflictAgent
from .agents.report_agent import ReportAgent


class Orchestrator:
    """Main orchestrator that coordinates the workflow between agents."""
    
    def __init__(self):
        """Initialize all agents."""
        self.dependency_agent = DependencyAgent()
        self.license_agent = LicenseAgent()
        self.conflict_agent = ConflictAgent()
        self.report_agent = ReportAgent()
    
    def run_compliance_analysis(self, project_path: str) -> Dict[str, Any]:
        """Run the full compliance analysis workflow.
        
        Args:
            project_path: Path to the project to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        # Step 1: Scan and resolve dependencies
        dependencies = self.dependency_agent.scan_dependencies(project_path)
        
        # Step 2: Identify licenses for each dependency
        licensed_dependencies = self.license_agent.identify_licenses(dependencies)
        
        # Step 3: Detect license conflicts
        conflicts = self.conflict_agent.detect_conflicts(licensed_dependencies)
        
        # Step 4: Generate compliance report
        report = self.report_agent.generate_report(
            licensed_dependencies, conflicts
        )
        
        return {
            "dependencies": licensed_dependencies,
            "conflicts": conflicts,
            "report": report
        }