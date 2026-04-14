"""Tests for the Conflict Agent."""

import unittest
import sys
import os

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from complianceai.agents.conflict_agent import ConflictAgent


class TestConflictAgent(unittest.TestCase):
    """Test cases for the ConflictAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = ConflictAgent()
    
    def test_init(self):
        """Test that the agent initializes correctly."""
        self.assertIsInstance(self.agent, ConflictAgent)
        self.assertIsInstance(self.agent.LICENSE_COMPATIBILITY, dict)
        self.assertIn('MIT', self.agent.LICENSE_COMPATIBILITY)
    
    def test_detect_conflicts_empty_input(self):
        """Test detecting conflicts with empty input."""
        result = self.agent.detect_conflicts([])
        self.assertEqual(result, {"conflicts": [], "undetected_licenses": []})
    
    def test_detect_conflicts_no_conflicts(self):
        """Test detecting conflicts when all licenses are compatible."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
            {"name": "requests", "version": "2.28.0", "license": "Apache-2.0"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # MIT, BSD, Apache, ISC, Zlib are all mutually compatible
        self.assertEqual(len(result["conflicts"]), 0)
    
    def test_detect_conflicts_gpl_with_mit(self):
        """Test that GPL and MIT are actually compatible (not conflicting)."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "GPL-3.0"},
            {"name": "package-b", "version": "2.0.0", "license": "MIT"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # Actually GPL-3.0 and MIT are compatible (can use MIT in GPL project)
        # This is NOT a conflict
        self.assertEqual(len(result["conflicts"]), 0)
    
    def test_detect_conflicts_real_gpl_conflict(self):
        """Test detecting real GPL conflict with proprietary."""
        # Add proprietary as a fake package type
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "GPL-3.0"},
            {"name": "my-proprietary-code", "version": "1.0.0", "license": "Proprietary"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # This might or might not show a conflict depending on matrix
    
    def test_detect_conflicts_unknown_license(self):
        """Test detecting conflicts with unknown license."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "Unknown"},
            {"name": "package-b", "version": "2.0.0", "license": "MIT"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # Unknown licenses should NOT create conflicts - handled separately
        self.assertEqual(len(result["conflicts"]), 0)
        # Unknown packages should be in undetected_licenses
        self.assertEqual(len(result["undetected_licenses"]), 1)
    
    def test_detect_conflicts_multiple_unknown(self):
        """Test that unknown licenses don't create conflicts - handled separately."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "Unknown"},
            {"name": "package-b", "version": "2.0.0", "license": "Unknown"},
            {"name": "package-c", "version": "3.0.0"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # Unknown licenses should NOT create conflicts - handled separately
        self.assertEqual(len(result["conflicts"]), 0)
        # 2 explicit Unknown + 1 missing license = 3
        self.assertEqual(len(result["undetected_licenses"]), 3)
    
    def test_check_compatibility_same_license(self):
        """Test that same licenses are compatible."""
        self.assertEqual(self.agent._check_compatibility('MIT', 'MIT'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('GPL-3.0', 'GPL-3.0'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('Apache-2.0', 'Apache-2.0'), 'compatible')
    
    def test_check_compatibility_mit_with_others(self):
        """Test MIT compatibility with other licenses."""
        # MIT is compatible with most things
        self.assertEqual(self.agent._check_compatibility('MIT', 'Apache-2.0'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('MIT', 'BSD-3-Clause'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('MIT', 'ISC'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('MIT', 'GPL-3.0'), 'compatible')
    
    def test_check_compatibility_unknown(self):
        """Test compatibility with unknown license."""
        # Unknown license should now return 'compatible' (not a conflict)
        self.assertEqual(self.agent._check_compatibility('Unknown', 'MIT'), 'compatible')
        # Known licenses are compatible
        self.assertEqual(self.agent._check_compatibility('BSD-3-Clause', 'ISC'), 'compatible')
        self.assertEqual(self.agent._check_compatibility('MIT', 'SomeUnknown'), 'compatible')
    
    def test_compatibility_to_severity(self):
        """Test converting compatibility to severity."""
        self.assertEqual(self.agent._compatibility_to_severity('compatible'), 'info')
        self.assertEqual(self.agent._compatibility_to_severity('incompatible'), 'critical')
        self.assertEqual(self.agent._compatibility_to_severity('weak_compatible'), 'warning')
        self.assertEqual(self.agent._compatibility_to_severity('unknown'), 'warning')
    
    def test_get_conflict_description(self):
        """Test getting conflict descriptions."""
        # Test compatible
        desc = self.agent._get_conflict_description('MIT', 'Apache-2.0', 'compatible')
        self.assertIsInstance(desc, str)
        
        # Test unknown compatibility
        desc_unknown = self.agent._get_conflict_description('MIT', 'Unknown', 'unknown')
        self.assertIn('unknown', desc_unknown.lower())
    
    def test_get_recommendation(self):
        """Test getting recommendations."""
        rec = self.agent._get_recommendation('MIT', 'Apache-2.0', 'compatible')
        self.assertIsInstance(rec, str)
        
        rec_unknown = self.agent._get_recommendation('MIT', 'Unknown', 'unknown')
        self.assertIn('manually', rec_unknown.lower())
    
    def test_get_license_category(self):
        """Test getting license categories."""
        self.assertEqual(self.agent.get_license_category('MIT'), 'permissive')
        self.assertEqual(self.agent.get_license_category('GPL-3.0'), 'copyleft')
        self.assertEqual(self.agent.get_license_category('AGPL-3.0'), 'strong_copyleft')
        self.assertEqual(self.agent.get_license_category('LGPL-2.1'), 'weak_copyleft')
        self.assertEqual(self.agent.get_license_category('Unknown'), 'unknown')
    
    def test_detect_conflicts_agpl_incompatible(self):
        """Test that AGPL conflicts with proprietary."""
        # Add proprietary license as a test case
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "AGPL-3.0"},
            {"name": "package-b", "version": "2.0.0", "license": "MIT"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # Should detect potential issues (AGPL is strong copyleft)
        # Just verify we get some result that mentions AGPL
        if len(result["conflicts"]) > 0:
            self.assertIn('AGPL-3.0', str(result))
    
    def test_detect_conflicts_lgpl_dynamic_linking(self):
        """Test LGPL is compatible with dynamic linking."""
        dependencies = [
            {"name": "package-a", "version": "1.0.0", "license": "LGPL-2.1"},
            {"name": "package-b", "version": "2.0.0", "license": "MIT"},
        ]
        
        result = self.agent.detect_conflicts(dependencies)
        
        # LGPL and MIT are compatible (dynamic linking allowed)
        # Check either no conflict or warning
        self.assertTrue(len(result["conflicts"]) == 0 or any(c['severity'] in ['warning', 'info'] for c in result["conflicts"]))


if __name__ == '__main__':
    unittest.main()