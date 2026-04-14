"""Orchestrator module that coordinates between different AI agents."""

import asyncio
from typing import Dict, Any
from .agents.dependency_agent import DependencyAgent
from .agents.dependency_crawler import DependencyCrawler
from .agents.license_agent import LicenseAgent
from .agents.conflict_agent import ConflictAgent
from .agents.report_agent import ReportAgent


class Orchestrator:
    """Main orchestrator that coordinates the workflow between agents."""
    
    def __init__(self):
        """Initialize all agents."""
        self.dependency_agent = DependencyAgent()
        self.dependency_crawler = DependencyCrawler()
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
        # Step 1: Parse initial dependencies from files
        initial_dependencies = self.dependency_agent.parse_input(project_path)
        
        # Step 2: Crawl the full dependency tree
        dependency_tree = asyncio.run(self.dependency_crawler.crawl_dependencies(initial_dependencies))
        
        # Step 3: Identify licenses for each dependency in the tree
        licensed_dependencies = self._flatten_dependency_tree(dependency_tree)
        licensed_dependencies = self.license_agent.identify_licenses(licensed_dependencies)
        
        # Step 4: Detect license conflicts
        conflicts = self.conflict_agent.detect_conflicts(licensed_dependencies)
        
        # Step 5: Generate compliance report
        report = self.report_agent.generate_report(
            licensed_dependencies, conflicts
        )
        
        return {
            "dependencies": licensed_dependencies,
            "conflicts": conflicts,
            "report": report,
            "dependency_tree": dependency_tree  # Include the full tree for reference
        }
    
    def _flatten_dependency_tree(self, tree: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Flatten the dependency tree into a list for license checking.
        
        Args:
            tree: The dependency tree from the crawler
            
        Returns:
            List of dictionaries with package name and version
        """
        flattened = []
        for name, info in tree.items():
            flattened.append({
                "name": name,
                "version": info.get("version")
            })
        return flattened