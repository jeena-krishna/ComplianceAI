"""Tests for the Orchestrator module."""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from complianceai.orchestrator import Orchestrator


class TestOrchestrator(unittest.TestCase):
    """Test cases for the Orchestrator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = Orchestrator()
    
    def test_orchestrator_initialization(self):
        """Test that the orchestrator initializes all agents."""
        self.assertIsInstance(self.orchestrator.dependency_agent, 
                            self.orchestrator.__class__.__dict__['__annotations__'].get('dependency_agent', object))
        # More specific tests would go here once agents are implemented
    
    @patch('complianceai.orchestrator.DependencyAgent')
    @patch('complianceai.orchestrator.LicenseAgent')
    @patch('complianceai.orchestrator.ConflictAgent')
    @patch('complianceai.orchestrator.ReportAgent')
    def test_run_compliance_analysis_calls_agents(self, mock_report, mock_conflict, 
                                                mock_license, mock_dependency):
        """Test that run_compliance_analysis calls all agent methods."""
        # Setup mocks
        mock_dep_instance = Mock()
        mock_dep_instance.scan_dependencies.return_value = {"test": "data"}
        mock_dependency.return_value = mock_dep_instance
        
        mock_lic_instance = Mock()
        mock_lic_instance.identify_licenses.return_value = {"test": "data"}
        mock_license.return_value = mock_lic_instance
        
        mock_conf_instance = Mock()
        mock_conf_instance.detect_conflicts.return_value = []
        mock_conflict.return_value = mock_conf_instance
        
        mock_rep_instance = Mock()
        mock_rep_instance.generate_report.return_value = {"report": "data"}
        mock_report.return_value = mock_rep_instance
        
        # Run the method
        result = self.orchestrator.run_compliance_analysis("/test/path")
        
        # Verify all methods were called
        mock_dep_instance.scan_dependencies.assert_called_once_with("/test/path")
        mock_lic_instance.identify_licenses.assert_called_once_with({"test": "data"})
        mock_conf_instance.detect_conflicts.assert_called_once_with({"test": "data"})
        mock_rep_instance.generate_report.assert_called_once()
        
        # Verify result structure
        self.assertIn("dependencies", result)
        self.assertIn("conflicts", result)
        self.assertIn("report", result)


if __name__ == '__main__':
    unittest.main()