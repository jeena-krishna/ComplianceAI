"""Tests for the Report Agent."""

import unittest
import sys
import os
import json

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from complianceai.agents.report_agent import ReportAgent


class TestReportAgent(unittest.TestCase):
    """Test cases for the ReportAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = ReportAgent()
    
    def test_init(self):
        """Test that the agent initializes correctly."""
        self.assertIsInstance(self.agent, ReportAgent)
        self.assertIn('LOW', self.agent.RISK_THRESHOLDS)
    
    def test_generate_report_empty_dependencies(self):
        """Test generating report with no dependencies."""
        result = self.agent.generate_report([], [])
        
        self.assertIn('timestamp', result)
        self.assertIn('summary', result)
        self.assertEqual(result['summary']['total_dependencies'], 0)
        self.assertEqual(result['summary']['risk_level'], 'LOW')
    
    def test_generate_report_with_dependencies(self):
        """Test generating report with dependencies but no conflicts."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
            {"name": "requests", "version": "2.28.0", "license": "Apache-2.0"},
        ]
        
        result = self.agent.generate_report(dependencies, [])
        
        self.assertEqual(result['summary']['total_dependencies'], 2)
        self.assertEqual(result['summary']['risk_level'], 'LOW')
        self.assertIn('recommendations', result)
    
    def test_generate_report_with_conflicts(self):
        """Test generating report with conflicts."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "GPL-3.0"},
            {"name": "package-b", "version": "2.0.0", "license": "Unknown"},
        ]
        
        conflicts = [
            {
                "severity": "warning",
                "description": "2 packages have unknown licenses",
                "packages": ["package-b"],
                "recommendation": "Verify license manually"
            }
        ]
        
        result = self.agent.generate_report(dependencies, conflicts)
        
        self.assertEqual(result['summary']['total_dependencies'], 2)
        self.assertEqual(result['summary']['warning_count'], 1)
    
    def test_generate_report_risk_level_low(self):
        """Test risk level calculation for LOW."""
        result = self.agent.generate_report([], [])
        self.assertEqual(result['summary']['risk_level'], 'LOW')
    
    def test_generate_report_risk_level_medium(self):
        """Test risk level calculation for MEDIUM."""
        conflicts = [
            {"severity": "warning", "description": "Test", "recommendation": "Test"}
        ]
        dependencies = [{"name": "test", "version": "1.0.0", "license": "MIT"}]
        
        result = self.agent.generate_report(dependencies, conflicts)
        
        # With 1 warning, risk should be at least MEDIUM
        self.assertIn(result['summary']['risk_level'], ['MEDIUM', 'HIGH', 'CRITICAL'])
    
    def test_generate_text_report(self):
        """Test generating plain text report."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
        ]
        
        result = self.agent.generate_text_report(dependencies, [])
        
        self.assertIsInstance(result, str)
        self.assertIn("LICENSE COMPLIANCE REPORT", result)
        self.assertIn("SUMMARY", result)
        self.assertIn("BSD-3-Clause", result)
    
    def test_generate_json_report(self):
        """Test generating JSON report."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
        ]
        
        result = self.agent.generate_json_report(dependencies, [])
        
        self.assertIsInstance(result, str)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        self.assertIn('summary', parsed)
        self.assertIn('findings', parsed)
    
    def test_generate_json_report_is_valid(self):
        """Test that JSON report can be parsed."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
            {"name": "requests", "version": "2.28.0", "license": "Apache-2.0"},
        ]
        
        json_str = self.agent.generate_json_report(dependencies, [])
        
        parsed = json.loads(json_str)
        
        # Check structure
        self.assertEqual(parsed['summary']['total_dependencies'], 2)
        self.assertEqual(parsed['summary']['risk_level'], 'LOW')
        self.assertIn('recommendations', parsed)
        self.assertIn('dependencies', parsed)
    
    def test_text_report_shows_conflicts(self):
        """Test that text report shows conflicts."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "GPL-3.0"},
            {"name": "package-b", "version": "2.0.0", "license": "Unknown"},
        ]
        
        conflicts = [
            {
                "severity": "warning",
                "description": "2 packages have unknown licenses",
                "packages": ["package-b"],
                "recommendation": "Verify manually"
            }
        ]
        
        result = self.agent.generate_text_report(dependencies, conflicts)
        
        self.assertIn("WARNING", result)
        self.assertIn("FINDINGS", result)
    
    def test_text_report_no_conflicts(self):
        """Test that text report shows no conflicts message."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "MIT"},
        ]
        
        result = self.agent.generate_text_report(dependencies, [])
        
        self.assertIn("No license conflicts detected", result)
    
    def test_calculate_risk_level_empty(self):
        """Test risk calculation with no conflicts."""
        self.assertEqual(self.agent._calculate_risk_level([]), 'LOW')
    
    def test_calculate_risk_level_critical(self):
        """Test risk calculation with critical conflicts."""
        conflicts = [{"severity": "critical"}] * 6
        self.assertEqual(self.agent._calculate_risk_level(conflicts), 'CRITICAL')
    
    def test_calculate_risk_level_high(self):
        """Test risk calculation with high conflicts."""
        conflicts = [{"severity": "critical"}] * 4
        self.assertEqual(self.agent._calculate_risk_level(conflicts), 'HIGH')
    
    def test_calculate_risk_level_medium(self):
        """Test risk calculation with moderate conflicts."""
        conflicts = [{"severity": "warning"}] * 2
        self.assertEqual(self.agent._calculate_risk_level(conflicts), 'MEDIUM')
    
    def test_count_licenses(self):
        """Test counting licenses."""
        dependencies = [
            {"name": "numpy", "license": "BSD-3-Clause"},
            {"name": "requests", "license": "Apache-2.0"},
            {"name": "flask", "license": "BSD-3-Clause"},
        ]
        
        counts = self.agent._count_licenses(dependencies)
        
        self.assertEqual(counts['BSD-3-Clause'], 2)
        self.assertEqual(counts['Apache-2.0'], 1)
    
    def test_format_dependencies(self):
        """Test formatting dependencies for report."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause", "license_source": "package"},
        ]
        
        formatted = self.agent._format_dependencies(dependencies)
        
        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]['name'], "numpy")
        self.assertEqual(formatted[0]['version'], "1.24.0")
        self.assertEqual(formatted[0]['license'], "BSD-3-Clause")
    
    def test_report_includes_recommendations(self):
        """Test that report includes recommendations."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "MIT"},
        ]
        
        result = self.agent.generate_report(dependencies, [])
        
        self.assertIn('recommendations', result)
        self.assertTrue(len(result['recommendations']) > 0)
    
    def test_report_with_unknown_licenses(self):
        """Test report with unknown license packages."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "Unknown"},
            {"name": "requests", "version": "2.28.0"},
        ]
        
        result = self.agent.generate_report(dependencies, [])
        
        self.assertIn('findings', result)
        # Unknown should be detected
        unknown = result['findings']['unknown_packages']
        self.assertTrue(len(unknown) >= 1)
    
    def test_report_timestamp(self):
        """Test that report has timestamp."""
        result = self.agent.generate_report([{"name": "test", "license": "MIT"}], [])
        
        self.assertIn('timestamp', result)
        self.assertIsNotNone(result['timestamp'])


if __name__ == '__main__':
    unittest.main()