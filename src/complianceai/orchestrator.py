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
        """Run the full compliance analysis pipeline synchronously.
        
        Args:
            input_data: File path to dependency file or raw text
            output_format: Output format - 'dict', 'text', or 'json'
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self._run_async(input_data, output_format))
        except RuntimeError:
            return asyncio.run(self._run_async(input_data, output_format))
    
    async def _run_async(self, input_data: str, output_format: str = 'dict') -> Dict[str, Any]:
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
        
        # Step 2: Crawl dependency tree (async)
        dependency_tree = await self._crawl_dependencies(initial_dependencies)
        if dependency_tree is None:
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
        
        # Format output - convert dict to list for report generation
        deps_list = [
            {'name': name, 'license': info.get('license')}
            for name, info in licensed_dependencies.items()
        ]
        
        if output_format == 'text':
            return self.report_agent.generate_text_report(
                deps_list, conflicts, dependency_tree
            )
        elif output_format == 'json':
            return self.report_agent.generate_json_report(
                deps_list, conflicts, dependency_tree
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
    
    async def _crawl_dependencies(self, dependencies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Step 2: Crawl dependency tree.
        
        Args:
            dependencies: List of dependencies
            
        Returns:
            Dependency tree dictionary
        """
        if not dependencies:
            return {}
        
        try:
            return await self.dependency_crawler.crawl_dependencies(dependencies)
        except Exception as e:
            error_msg = f"crawl_dependencies: {str(e)}"
            logger.error(error_msg)
            self.errors.append({
                "step": "crawl_dependencies",
                "error": str(e)
            })
            return {}
        finally:
            try:
                await self.dependency_crawler.close()
            except Exception:
                pass
    
    def _identify_licenses(self, dependency_tree: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
        """Step 3: Identify licenses for dependencies.
        
        Args:
            dependency_tree: Dictionary of dependencies from crawler
            
        Returns:
            Dictionary with normalized licenses, keys are package names
        """
        if not dependency_tree:
            return {}
        
        return self._safe_execute(
            "identify_licenses",
            self.license_agent.identify_licenses,
            dependency_tree,
            default_return={}
        )
    
    def _detect_conflicts(self, licensed_dependencies: Dict[str, Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Step 4: Detect license conflicts.
        
        Args:
            licensed_dependencies: Dictionary of dependencies with licenses
            
        Returns:
            List of conflicts
        """
        deps_list = [
            {'name': name, 'license': info.get('license')}
            for name, info in licensed_dependencies.items()
        ]
        
        return self._safe_execute(
            "detect_conflicts",
            self.conflict_agent.detect_conflicts,
            deps_list,
            default_return=[]
        )
    
    def _generate_report(self, licensed_dependencies: Dict[str, Dict[str, Any]], 
                        conflicts: List[Dict[str, Any]],
                        dependency_tree: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 5: Generate compliance report.
        
        Args:
            licensed_dependencies: Dictionary of dependencies with licenses
            conflicts: List of conflicts
            dependency_tree: Dependency tree dictionary
            
        Returns:
            Report dictionary
        """
        deps_list = [
            {'name': name, 'license': info.get('license')}
            for name, info in licensed_dependencies.items()
        ]
        
        return self._safe_execute(
            "generate_report",
            self.report_agent.generate_report,
            deps_list,
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
            List of dictionaries with package name, version, license, and classifiers
        """
        flattened = []
        for name, info in tree.items():
            flattened.append({
                "name": name,
                "version": info.get("version"),
                "license": info.get("license"),
                "classifiers": info.get("classifiers", []),
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