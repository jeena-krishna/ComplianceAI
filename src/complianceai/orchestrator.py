"""Orchestrator module that coordinates between different AI agents."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from .agents.dependency_agent import DependencyAgent
from .agents.dependency_crawler import DependencyCrawler
from .agents.license_agent import LicenseAgent
from .agents.conflict_agent import ConflictAgent
from .agents.report_agent import ReportAgent

# Set up logging
logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass


class DependencyParseError(OrchestratorError):
    """Error parsing dependencies."""
    pass


class DependencyCrawlError(OrchestratorError):
    """Error crawling dependencies."""
    pass


class LicenseIdentificationError(OrchestratorError):
    """Error identifying licenses."""
    pass


class ConflictDetectionError(OrchestratorError):
    """Error detecting conflicts."""
    pass


class ReportGenerationError(OrchestratorError):
    """Error generating report."""
    pass


class Orchestrator:
    """Main orchestrator that coordinates the workflow between agents."""
    
    def __init__(self, max_depth: int = 3):
        """Initialize all agents.
        
        Args:
            max_depth: Maximum depth for dependency crawling
        """
        self.dependency_agent = DependencyAgent()
        self.dependency_crawler = DependencyCrawler(max_depth=max_depth)
        self.license_agent = LicenseAgent()
        self.conflict_agent = ConflictAgent()
        self.report_agent = ReportAgent()
        
        # Track errors at each step
        self.errors = []
    
    def run(self, input_data: str, output_format: str = 'dict') -> Dict[str, Any]:
        """Run the full compliance analysis pipeline.
        
        Args:
            input_data: File path to dependency file or raw text containing dependencies
            output_format: Output format - 'dict', 'text', or 'json'
            
        Returns:
            Dictionary containing analysis results, or raises OrchestratorError
        """
        # Reset errors
        self.errors = []
        
        # Step 1: Parse dependencies
        initial_dependencies = self._parse_dependencies(input_data)
        if initial_dependencies is None:
            raise DependencyParseError(f"Failed to parse dependencies from input")
        
        # Step 2: Crawl dependency tree
        dependency_tree = self._crawl_dependencies(initial_dependencies)
        if dependency_tree is None:
            # Use raw dependencies if crawl fails
            dependency_tree = {}
        
        # Step 3: Identify licenses
        licensed_dependencies = self._identify_licenses(dependency_tree)
        if licensed_dependencies is None:
            raise LicenseIdentificationError("Failed to identify licenses")
        
        # Step 4: Detect conflicts
        conflicts = self._detect_conflicts(licensed_dependencies)
        if conflicts is None:
            raise ConflictDetectionError("Failed to detect conflicts")
        
        # Step 5: Generate report
        report = self._generate_report(licensed_dependencies, conflicts, dependency_tree)
        if report is None:
            raise ReportGenerationError("Failed to generate report")
        
        # Format output
        if output_format == 'text':
            return self.report_agent.generate_text_report(
                licensed_dependencies, conflicts, dependency_tree
            )
        elif output_format == 'json':
            return self.report_agent.generate_json_report(
                licensed_dependencies, conflicts, dependency_tree
            )
        
        # Return full dict
        return {
            "success": True,
            "dependencies": licensed_dependencies,
            "conflicts": conflicts,
            "report": report,
            "dependency_tree": dependency_tree,
            "errors": self.errors if self.errors else None,
        }
    
    def _safe_execute(self, step_name: str, func, *args, default_return=None):
        """Execute a function with error handling.
        
        Args:
            step_name: Name of the step for logging
            func: Function to execute
            default_return: Default return value if function fails
            
        Returns:
            Result of function or default_return on error
        """
        try:
            return func(*args)
        except Exception as e:
            error_msg = f"{step_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append({
                "step": step_name,
                "error": str(e)
            })
            return default_return
    
    def _parse_dependencies(self, input_data: str) -> Optional[List[Dict[str, Any]]]:
        """Step 1: Parse dependencies from input.
        
        Args:
            input_data: File path or raw text
            
        Returns:
            List of parsed dependencies
        """
        return self._safe_execute(
            "parse_dependencies",
            self.dependency_agent.parse_input,
            input_data,
            default_return=[]
        )
    
    def _crawl_dependencies(self, dependencies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Step 2: Crawl dependency tree.
        
        Args:
            dependencies: List of dependencies
            
        Returns:
            Dependency tree dictionary
        """
        if not dependencies:
            return {}
        
        try:
            return asyncio.run(
                self.dependency_crawler.crawl_dependencies(dependencies)
            )
        except Exception as e:
            error_msg = f"crawl_dependencies: {str(e)}"
            logger.error(error_msg)
            self.errors.append({
                "step": "crawl_dependencies",
                "error": str(e)
            })
            # Return empty tree
            return {}
        finally:
            # Clean up the crawler session
            try:
                asyncio.run(self.dependency_crawler.close())
            except Exception:
                pass
    
    def _identify_licenses(self, dependency_tree: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Step 3: Identify licenses for dependencies.
        
        Args:
            dependency_tree: Dictionary of dependencies
            
        Returns:
            List of dependencies with licenses
        """
        flattened = self._flatten_dependency_tree(dependency_tree)
        if not flattened:
            return []
        
        return self._safe_execute(
            "identify_licenses",
            self.license_agent.identify_licenses,
            flattened,
            default_return=flattened
        )
    
    def _detect_conflicts(self, licensed_dependencies: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Step 4: Detect license conflicts.
        
        Args:
            licensed_dependencies: List of dependencies with licenses
            
        Returns:
            List of conflicts
        """
        return self._safe_execute(
            "detect_conflicts",
            self.conflict_agent.detect_conflicts,
            licensed_dependencies,
            default_return=[]
        )
    
    def _generate_report(self, licensed_dependencies: List[Dict[str, Any]], 
                        conflicts: List[Dict[str, Any]],
                        dependency_tree: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 5: Generate compliance report.
        
        Args:
            licensed_dependencies: List of dependencies with licenses
            conflicts: List of conflicts
            dependency_tree: Dependency tree dictionary
            
        Returns:
            Report dictionary
        """
        return self._safe_execute(
            "generate_report",
            self.report_agent.generate_report,
            licensed_dependencies,
            conflicts,
            dependency_tree,
            default_return={
                "error": "Report generation failed",
                "timestamp": "unknown"
            }
        )
    
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
    
    def get_errors(self) -> List[Dict[str, str]]:
        """Get any errors that occurred during execution.
        
        Returns:
            List of error dictionaries
        """
        return self.errors
    
    def clear_errors(self):
        """Clear the error list."""
        self.errors = []