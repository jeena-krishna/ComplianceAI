"""Tests for the Orchestrator module."""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the external dependencies that might not be available in test environment
sys.modules['requests'] = Mock()
sys.modules['aiohttp'] = Mock()

from complianceai.orchestrator import Orchestrator
from complianceai.agents.dependency_agent import DependencyAgent


class TestOrchestrator(unittest.TestCase):
    """Test cases for the Orchestrator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = Orchestrator()
    
    def test_orchestrator_initialization(self):
        """Test that the orchestrator initializes all agents."""
        self.assertIsInstance(self.orchestrator.dependency_agent, 
                            DependencyAgent)
        # More specific tests would go here once agents are implemented
    
    def test_run_compliance_analysis_calls_agents(self):
        """Test that run_compliance_analysis calls all agent methods."""
        # Create the orchestrator
        orchestrator = Orchestrator()
        
        # Replace the dependency agent with a mock
        mock_dep = Mock()
        mock_dep.parse_input.return_value = [{"name": "test", "version": "1.0.0"}]
        orchestrator.dependency_agent = mock_dep
        
        # Replace the crawler with a mock that returns a coroutine
        mock_crawler = Mock()
        # Create a mock coroutine for crawl_dependencies
        async def mock_crawl_dependencies(*args, **kwargs):
            return {
                "test": {
                    "version": "1.0.0",
                    "license": "MIT",
                    "dependencies": [],
                    "depth": 1
                }
            }
        mock_crawler.crawl_dependencies = mock_crawl_dependencies
        # Wrap the async function in a Mock to track calls
        mock_crawler.crawl_dependencies = Mock(side_effect=mock_crawl_dependencies)
        orchestrator.dependency_crawler = mock_crawler
        
        # Replace the license agent with a mock
        mock_lic = Mock()
        mock_lic.identify_licenses.return_value = [{"name": "test", "version": "1.0.0", "license": "MIT"}]
        orchestrator.license_agent = mock_lic
        
        # Replace the conflict agent with a mock
        mock_conf = Mock()
        mock_conf.detect_conflicts.return_value = []
        orchestrator.conflict_agent = mock_conf
        
        # Replace the report agent with a mock
        mock_rep = Mock()
        mock_rep.generate_report.return_value = {"report": "data"}
        orchestrator.report_agent = mock_rep
        
        # Run the method
        result = orchestrator.run_compliance_analysis("/test/path")
        
        # Verify all methods were called
        mock_dep.parse_input.assert_called_once_with("/test/path")
        mock_crawler.crawl_dependencies.assert_called_once()
        mock_lic.identify_licenses.assert_called_once_with([{"name": "test", "version": "1.0.0"}])
        mock_conf.detect_conflicts.assert_called_once_with([{"name": "test", "version": "1.0.0", "license": "MIT"}])
        mock_rep.generate_report.assert_called_once()
        
        # Verify result structure
        self.assertIn("dependencies", result)
        self.assertIn("conflicts", result)
        self.assertIn("report", result)
        self.assertIn("dependency_tree", result)


if __name__ == '__main__':
    unittest.main()