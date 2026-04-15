"""Tests for the Orchestrator."""

import unittest
import sys
import os
import json

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from complianceai.orchestrator import Orchestrator, OrchestratorError


class TestOrchestrator(unittest.TestCase):
    """Test cases for the Orchestrator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = Orchestrator(max_depth=2)
        # Clear any errors from initialization
        self.orchestrator.clear_errors()
    
    def test_init(self):
        """Test that the orchestrator initializes correctly."""
        self.assertIsInstance(self.orchestrator, Orchestrator)
        self.assertIsNotNone(self.orchestrator.dependency_agent)
        self.assertIsNotNone(self.orchestrator.license_agent)
        self.assertIsNotNone(self.orchestrator.conflict_agent)
        self.assertIsNotNone(self.orchestrator.report_agent)
    
    def test_init_with_max_depth(self):
        """Test that max_depth is set correctly."""
        orch = Orchestrator(max_depth=3)
        self.assertEqual(orch.dependency_crawler.max_depth, 3)
    
    def test_run_with_raw_text(self):
        """Test running with raw text input."""
        result = self.orchestrator.run("numpy==1.24.0\nrequests>=2.28.0")
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertIn('dependencies', result)
        self.assertIn('report', result)
    
    def test_run_returns_dependencies(self):
        """Test that run returns dependencies."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        # Should have at least the parsed dependency
        self.assertTrue(len(result['dependencies']) > 0)
    
    def test_run_returns_report(self):
        """Test that run returns a report."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        self.assertIn('report', result)
        self.assertIn('summary', result['report'])
    
    def test_run_returns_conflicts(self):
        """Test that run returns conflicts list."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        self.assertIn('conflicts', result)
        # New format: dict with 'conflicts' and 'undetected_licenses'
        self.assertIsInstance(result['conflicts'], dict)
        self.assertIn('conflicts', result['conflicts'])
    
    def test_run_text_format(self):
        """Test running with text output format."""
        result = self.orchestrator.run(
            "numpy==1.24.0", 
            output_format='text'
        )
        
        self.assertIsInstance(result, str)
        self.assertIn("LICENSE COMPLIANCE REPORT", result)
    
    def test_run_json_format(self):
        """Test running with JSON output format."""
        result = self.orchestrator.run(
            "numpy==1.24.0", 
            output_format='json'
        )
        
        self.assertIsInstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        self.assertIn('summary', parsed)
    
    def test_run_with_multiple_dependencies(self):
        """Test running with multiple dependencies."""
        input_text = """numpy==1.24.0
requests>=2.28.0
flask>=2.0.0"""
        
        result = self.orchestrator.run(input_text)
        
        self.assertTrue(len(result['dependencies']) >= 3)
    
    def test_run_empty_input(self):
        """Test running with empty input."""
        result = self.orchestrator.run("")
        
        # Should handle empty input gracefully
        self.assertIn('success', result)
        if result['success']:
            self.assertIn('dependencies', result)
    
    def test_run_includes_dependency_tree(self):
        """Test that run includes dependency tree."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        self.assertIn('dependency_tree', result)
    
    def test_get_errors(self):
        """Test getting errors after execution."""
        # Run with something that might cause errors
        result = self.orchestrator.run("numpy==1.24.0")
        
        # Errors should be tracked
        errors = self.orchestrator.get_errors()
        self.assertIsInstance(errors, list)
    
    def test_clear_errors(self):
        """Test clearing errors."""
        # Add a mock error
        self.orchestrator.errors.append({"step": "test", "error": "test error"})
        
        # Clear them
        self.orchestrator.clear_errors()
        
        self.assertEqual(len(self.orchestrator.errors), 0)
    
    def test_flatten_dependency_tree(self):
        """Test flattening dependency tree."""
        tree = {
            "numpy": {"version": "1.24.0", "license": "BSD-3-Clause"},
            "requests": {"version": "2.28.0", "license": "Apache-2.0"},
        }
        
        flattened = self.orchestrator._flatten_dependency_tree(tree)
        
        self.assertEqual(len(flattened), 2)
        self.assertEqual(flattened[0]['name'], "numpy")
        self.assertEqual(flattened[0]['version'], "1.24.0")
    
    def test_flatten_empty_tree(self):
        """Test flattening empty tree."""
        flattened = self.orchestrator._flatten_dependency_tree({})
        
        self.assertEqual(flattened, [])
    
    def test_report_has_risk_level(self):
        """Test that report includes risk level."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        risk_level = result['report']['summary']['risk_level']
        self.assertIn(risk_level, ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
    
    def test_report_has_license_counts(self):
        """Test that report includes license breakdown."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        license_counts = result['report']['summary']['license_counts']
        self.assertIsInstance(license_counts, dict)
    
    def test_report_has_recommendations(self):
        """Test that report includes recommendations."""
        result = self.orchestrator.run("numpy==1.24.0")
        
        recommendations = result['report']['recommendations']
        self.assertIsInstance(recommendations, list)
    
    def test_max_depth_limit(self):
        """Test that max_depth parameter is used."""
        orch_low = Orchestrator(max_depth=1)
        orch_high = Orchestrator(max_depth=5)
        
        self.assertEqual(orch_low.dependency_crawler.max_depth, 1)
        self.assertEqual(orch_high.dependency_crawler.max_depth, 5)


if __name__ == '__main__':
    unittest.main()