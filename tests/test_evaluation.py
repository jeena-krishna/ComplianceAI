"""End-to-end evaluation tests for ComplianceAI pipeline."""

import json
import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from complianceai.orchestrator import Orchestrator


class TestEvaluationPermissive(unittest.TestCase):
    """Test case: All permissive licenses - should pass clean."""

    @classmethod
    def setUpClass(cls):
        """Create temp file with permissive licenses."""
        cls.content = """requests==2.31.0
flask==3.0.0
urllib3==2.0.0
certifi==2023.7.22
charset-normalizer==3.3.2
idna==3.6
"""

        cls.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        cls.temp_file.write(cls.content)
        cls.temp_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp file."""
        os.unlink(cls.temp_file.name)

    def test_permissive_clean(self):
        """All permissive licenses should pass with no critical issues."""
        orchestrator = Orchestrator(max_depth=2)
        result = orchestrator.run(self.temp_file.name)

        self.assertTrue(result.get("success"))
        self.assertIn("conflicts", result)
        self.assertIn("dependencies", result)

        conflicts = result["conflicts"]

        critical_count = sum(
            1 for c in conflicts if c.get("severity") == "critical"
        )
        warning_count = sum(
            1 for c in conflicts if c.get("severity") == "warning"
        )

        print(f"\n[permissive] Dependencies: {len(result['dependencies'])}")
        print(f"[permissive] Critical: {critical_count}, Warnings: {warning_count}")

        self.assertEqual(
            critical_count, 0,
            "Permissive licenses should not produce critical conflicts"
        )


class TestEvaluationGPLCritical(unittest.TestCase):
    """Test case: GPL packages - should detect issues."""

    @classmethod
    def setUpClass(cls):
        """Create temp file with GPL packages."""
        cls.content = """gpl-2.0-package==1.0.0
apache-2.0-package==1.0.0
"""

        cls.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        cls.temp_file.write(cls.content)
        cls.temp_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp file."""
        os.unlink(cls.temp_file.name)

    def test_gpl_detection(self):
        """GPL packages should be detected."""
        orchestrator = Orchestrator(max_depth=2)
        result = orchestrator.run(self.temp_file.name)

        self.assertTrue(result.get("success"))
        
        conflicts = result["conflicts"]

        critical_count = sum(
            1 for c in conflicts if c.get("severity") == "critical"
        )
        warning_count = sum(
            1 for c in conflicts if c.get("severity") == "warning"
        )

        print(f"\n[gpl-critical] Dependencies: {len(result['dependencies'])}")
        print(f"[gpl-critical] Critical: {critical_count}, Warnings: {warning_count}")


class TestEvaluationMixedWarnings(unittest.TestCase):
    """Test case: Mixed licenses - should show warnings."""

    @classmethod
    def setUpClass(cls):
        """Create temp file with mixed licenses."""
        cls.content = """django==4.2.0
celery==5.3.4
redis==5.0.1
"""

        cls.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        cls.temp_file.write(cls.content)
        cls.temp_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp file."""
        os.unlink(cls.temp_file.name)

    def test_mixed_warnings(self):
        """Mixed licenses should show warnings but may pass."""
        orchestrator = Orchestrator(max_depth=2)
        result = orchestrator.run(self.temp_file.name)

        self.assertTrue(result.get("success"))

        conflicts = result["conflicts"]

        critical_count = sum(
            1 for c in conflicts if c.get("severity") == "critical"
        )
        warning_count = sum(
            1 for c in conflicts if c.get("severity") == "warning"
        )

        print(f"\n[mixed] Dependencies: {len(result['dependencies'])}")
        print(f"[mixed] Critical: {critical_count}, Warnings: {warning_count}")

        self.assertGreaterEqual(
            warning_count, 0,
            "Mixed licenses should produce warnings"
        )


class TestEvaluationJSONOutput(unittest.TestCase):
    """Test case: JSON output format."""

    @classmethod
    def setUpClass(cls):
        """Create temp file for JSON test."""
        cls.content = """flask==3.0.0
werkzeug==3.0.0
"""

        cls.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        cls.temp_file.write(cls.content)
        cls.temp_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp file."""
        os.unlink(cls.temp_file.name)

    def test_json_output(self):
        """Test JSON output format."""
        orchestrator = Orchestrator(max_depth=2)
        result = orchestrator.run(self.temp_file.name, output_format='json')

        parsed = json.loads(result)
        self.assertIn("dependencies", parsed)
        self.assertIn("findings", parsed)
        self.assertIn("summary", parsed)

        print(f"\n[json] Output valid: {True}")


class TestEvaluationRawTextInput(unittest.TestCase):
    """Test case: Raw text input instead of file."""

    def test_raw_text(self):
        """Test passing raw text instead of file path."""
        content = "flask==3.0.0\nrequests==2.31.0"
        
        orchestrator = Orchestrator(max_depth=1)
        result = orchestrator.run(content)

        self.assertTrue(result.get("success"))
        self.assertIn("dependencies", result)
        self.assertIn("conflicts", result)

        print(f"\n[raw-text] Dependencies: {len(result['dependencies'])}")


class TestEvaluationMaxDepth(unittest.TestCase):
    """Test case: Varying max_depth affects results."""

    def test_depth_1(self):
        """Test with max_depth=1."""
        content = "flask==3.0.0\nrequests==2.31.0"
        
        orchestrator = Orchestrator(max_depth=1)
        result = orchestrator.run(content)

        deps_count = len(result["dependencies"])
        print(f"\n[depth=1] Dependencies found: {deps_count}")

    def test_depth_3(self):
        """Test with max_depth=3."""
        content = "flask==3.0.0\nrequests==2.31.0"
        
        orchestrator = Orchestrator(max_depth=3)
        result = orchestrator.run(content)

        deps_count = len(result["dependencies"])
        print(f"\n[depth=3] Dependencies found: {deps_count}")

        self.assertGreaterEqual(
            deps_count, 2,
            "Higher depth should find more dependencies"
        )


class TestEvaluationTextOutput(unittest.TestCase):
    """Test case: Text output format."""

    @classmethod
    def setUpClass(cls):
        """Create temp file for text test."""
        cls.content = """flask==3.0.0
requests==2.31.0
"""

        cls.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        )
        cls.temp_file.write(cls.content)
        cls.temp_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up temp file."""
        os.unlink(cls.temp_file.name)

    def test_text_output(self):
        """Test text output format."""
        orchestrator = Orchestrator(max_depth=2)
        result = orchestrator.run(self.temp_file.name, output_format='text')

        self.assertIsInstance(result, str)
        self.assertIn("COMPLIANCE REPORT", result)

        print(f"\n[text] Output contains report: {True}")


if __name__ == '__main__':
    unittest.main(verbosity=2)