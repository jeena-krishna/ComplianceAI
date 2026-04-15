"""Tests for the Dependency Agent."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open
import sys

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from complianceai.agents.dependency_agent import DependencyAgent


class TestDependencyAgent(unittest.TestCase):
    """Test cases for the DependencyAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = DependencyAgent()
    
    def test_init(self):
        """Test that the agent initializes correctly."""
        self.assertIsInstance(self.agent, DependencyAgent)
    
    def test_parse_requirements_txt_basic(self):
        """Test parsing a basic requirements.txt file."""
        content = """numpy==1.24.0
pandas>=1.3.0
requests
flask~=2.0.0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='requirements.txt', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                result = self.agent._parse_requirements_txt(f.name)
                
                expected = [
                    {"name": "numpy", "version": "1.24.0"},
                    {"name": "pandas", "version": "1.3.0"},
                    {"name": "requests", "version": None},
                    {"name": "flask", "version": "2.0.0"}
                ]
                
                self.assertEqual(result, expected)
            finally:
                os.unlink(f.name)
    
    def test_parse_requirements_txt_with_comments_and_empty_lines(self):
        """Test parsing requirements.txt with comments and empty lines."""
        content = """# This is a comment
numpy==1.24.0

# Another comment
pandas>=1.3.0
requests  # inline comment
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='requirements.txt', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                result = self.agent._parse_requirements_txt(f.name)
                
                expected = [
                    {"name": "numpy", "version": "1.24.0"},
                    {"name": "pandas", "version": "1.3.0"},
                    {"name": "requests", "version": None}
                ]
                
                self.assertEqual(result, expected)
            finally:
                os.unlink(f.name)
    
    def test_parse_package_json_basic(self):
        """Test parsing a basic package.json file."""
        content = {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "lodash": "^4.17.21",
                "express": "4.18.0",
                "react": "*"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "typescript": "4.8.0"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='package.json', delete=False) as f:
            json.dump(content, f)
            f.flush()
            
            try:
                result = self.agent._parse_package_json(f.name)
                
                # Should include both dependencies and devDependencies
                expected_names = {"lodash", "express", "react", "jest", "typescript"}
                actual_names = {item["name"] for item in result}
                self.assertEqual(actual_names, expected_names)
                
                # Check specific versions
                lodash_item = next(item for item in result if item["name"] == "lodash")
                self.assertEqual(lodash_item["version"], "^4.17.21")
                
                react_item = next(item for item in result if item["name"] == "react")
                self.assertIsNone(react_item["version"])  # * becomes None
                
                jest_item = next(item for item in result if item["name"] == "jest")
                self.assertEqual(jest_item["version"], "^29.0.0")
            finally:
                os.unlink(f.name)
    
    def test_parse_package_json_missing_sections(self):
        """Test parsing package.json with missing dependencies sections."""
        content = {
            "name": "test-project",
            "version": "1.0.0"
            # No dependencies or devDependencies
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='package.json', delete=False) as f:
            json.dump(content, f)
            f.flush()
            
            try:
                result = self.agent._parse_package_json(f.name)
                self.assertEqual(result, [])
            finally:
                os.unlink(f.name)
    
    def test_parse_raw_text_requirements_style(self):
        """Test parsing raw text in requirements.txt style."""
        content = """numpy==1.24.0
pandas>=1.3.0
requests
"""
        
        result = self.agent._parse_raw_text(content)
        
        expected = [
            {"name": "numpy", "version": "1.24.0"},
            {"name": "pandas", "version": "1.3.0"},
            {"name": "requests", "version": None}
        ]
        
        self.assertEqual(result, expected)
    
    def test_parse_raw_text_package_json_style(self):
        """Test parsing raw text that looks like package.json."""
        content = json.dumps({
            "dependencies": {
                "lodash": "^4.17.21",
                "express": "4.18.0"
            },
            "devDependencies": {
                "jest": "^29.0.0"
            }
        })
        
        result = self.agent._parse_raw_text(content)
        
        # Should have extracted both dependencies and devDependencies
        expected_names = {"lodash", "express", "jest"}
        actual_names = {item["name"] for item in result}
        self.assertEqual(actual_names, expected_names)
    
    def test_parse_raw_text_npm_at_syntax(self):
        """Test parsing raw text with npm @ syntax."""
        content = """lodash@^4.17.21
express@4.18.0
@types/node
"""
        
        result = self.agent._parse_raw_text(content)
        
        expected = [
            {"name": "lodash", "version": "^4.17.21"},
            {"name": "express", "version": "4.18.0"},
            {"name": "@types/node", "version": None}
        ]
        
        self.assertEqual(result, expected)
    
    def test_parse_file_requirements_txt(self):
        """Test the main parse_input method with a requirements.txt file."""
        content = """numpy==1.24.0
pandas>=1.3.0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='requirements.txt', delete=False) as f:
            f.write(content)
            f.flush()
            
            try:
                result = self.agent.parse_input(f.name)
                
                expected = [
                    {"name": "numpy", "version": "1.24.0"},
                    {"name": "pandas", "version": "1.3.0"}
                ]
                
                self.assertEqual(result, expected)
            finally:
                os.unlink(f.name)
    
    def test_parse_file_package_json(self):
        """Test the main parse_input method with a package.json file."""
        content = {
            "dependencies": {
                "lodash": "^4.17.21"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='package.json', delete=False) as f:
            json.dump(content, f)
            f.flush()
            
            try:
                result = self.agent.parse_input(f.name)
                
                expected = [
                    {"name": "lodash", "version": "^4.17.21"}
                ]
                
                self.assertEqual(result, expected)
            finally:
                os.unlink(f.name)
    
    def test_parse_raw_text_input(self):
        """Test the main parse_input method with raw text."""
        content = """numpy==1.24.0
pandas>=1.3.0
"""
        
        result = self.agent.parse_input(content)
        
        expected = [
            {"name": "numpy", "version": "1.24.0"},
            {"name": "pandas", "version": "1.3.0"}
        ]
        
        self.assertEqual(result, expected)
    
    def test_parse_github_url(self):
        """Test parsing GitHub URL returns actual dependencies."""
        import zipfile
        import io
        import requests as req
        
        requirements_content = "requests==2.31.0\nflask>=2.0.0\nnumpy==1.24.0"
        
        class MockZipResponse:
            def __init__(self, status_code):
                self.status_code = status_code
            
            @property
            def content(self):
                if self.status_code == 200:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('repo-main/requirements.txt', requirements_content)
                    return buf.getvalue()
                return b''
        
        original_get = req.get
        
        def mock_get(url, **kwargs):
            if 'archive/refs/heads/' in url:
                return MockZipResponse(200)
            return MockZipResponse(404)
        
        req.get = mock_get
        try:
            url = "https://github.com/user/repo"
            result = self.agent.parse_input(url)
            self.assertGreater(len(result), 0)
            names = [d['name'] for d in result]
            self.assertIn('requests', names)
        finally:
            req.get = original_get
    
    def test_parse_package_spec_various_formats(self):
        """Test parsing various package specification formats."""
        test_cases = [
            ("numpy==1.24.0", {"name": "numpy", "version": "1.24.0"}),
            ("pandas>=1.3.0", {"name": "pandas", "version": "1.3.0"}),
            ("requests<=2.28.0", {"name": "requests", "version": "2.28.0"}),
            ("flask>2.0.0", {"name": "flask", "version": "2.0.0"}),
            ("django<4.0.0", {"name": "django", "version": "4.0.0"}),
            ("library~=1.0.0", {"name": "library", "version": "1.0.0"}),
            ("tool!=1.0.0", {"name": "tool", "version": "1.0.0"}),
            ("package", {"name": "package", "version": None}),
            ("lodash@^4.17.21", {"name": "lodash", "version": "^4.17.21"}),
            ("@types/node", {"name": "@types/node", "version": None}),
        ]
        
        for spec, expected in test_cases:
            with self.subTest(spec=spec):
                result = self.agent._parse_package_spec(spec)
                self.assertEqual(result, expected)
    
    def test_parse_package_spec_invalid(self):
        """Test parsing invalid package specifications."""
        invalid_cases = [
            "",
            "   ",
            "# comment",
            "==1.0.0",  # missing name
            ">=1.0.0",  # missing name
            "@",        # just @ symbol
        ]
        
        for spec in invalid_cases:
            with self.subTest(spec=spec):
                result = self.agent._parse_package_spec(spec)
                self.assertIsNone(result)
    
    def test_is_github_url(self):
        """Test GitHub URL detection."""
        # Valid GitHub URLs
        valid_urls = [
            "https://github.com/user/repo",
            "http://github.com/user/repo",
            "https://www.github.com/user/repo",
            "https://github.com/user/repo/tree/main",
            "https://github.com/user/repo/issues/1"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.agent._is_github_url(url))
        
        # Invalid URLs
        invalid_urls = [
            "https://gitlab.com/user/repo",
            "https://example.com/user/repo",
            "not-a-url",
            "https://github.com",  # missing repo
            ""
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.agent._is_github_url(url))


class TestGitHubParsing(unittest.TestCase):
    """Test cases for GitHub URL parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = DependencyAgent()

    def test_parse_package_json_string(self):
        """Test parsing package.json string."""
        content = """{
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "~4.17.0"
            },
            "devDependencies": {
                "jest": ">=29.0.0"
            }
        }"""
        result = self.agent._parse_package_json_string(content)
        
        self.assertEqual(len(result), 3)
        names = [d['name'] for d in result]
        self.assertIn('express', names)
        self.assertIn('lodash', names)
        self.assertIn('jest', names)

    def test_parse_package_json_string_invalid(self):
        """Test parsing invalid package.json."""
        result = self.agent._parse_package_json_string("not json")
        self.assertEqual(result, [])

    def test_normalize_version(self):
        """Test version normalization."""
        self.assertEqual(self.agent._normalize_version("^1.0.0"), "1.0.0")
        self.assertEqual(self.agent._normalize_version("~4.17.0"), "4.17.0")
        self.assertEqual(self.agent._normalize_version(">=2.0.0"), "2.0.0")
        self.assertEqual(self.agent._normalize_version("=1.0.0"), "1.0.0")
        self.assertEqual(self.agent._normalize_version("1.0.0"), "1.0.0")

    def test_parse_github_url(self):
        """Test parsing GitHub URL using zip-based approach."""
        import zipfile
        import io
        import requests as req
        
        requirements_content = "requests==2.31.0\nflask>=2.0.0"
        
        class MockZipResponse:
            def __init__(self, status_code):
                self.status_code = status_code
            
            @property
            def content(self):
                if self.status_code == 200:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('repo-main/requirements.txt', requirements_content)
                    return buf.getvalue()
                return b''
        
        original_get = req.get
        
        def mock_get(url, **kwargs):
            if 'archive/refs/heads/' in url:
                return MockZipResponse(200)
            return MockZipResponse(404)
        
        req.get = mock_get
        try:
            result = self.agent._parse_github_url("https://github.com/owner/repo")
            self.assertGreater(len(result), 0)
            names = [d['name'] for d in result]
            self.assertIn('requests', names)
        finally:
            req.get = original_get

    def test_parse_github_url_not_found(self):
        """Test parsing GitHub URL when branch doesn't exist."""
        import requests as req
        
        class MockZipResponse:
            def __init__(self, status_code):
                self.status_code = status_code
                self.content = b''
        
        original_get = req.get
        
        def mock_get(url, **kwargs):
            if 'archive/refs/heads/' in url:
                return MockZipResponse(404)
            return MockZipResponse(404)
        
        req.get = mock_get
        try:
            result = self.agent._parse_github_url("https://github.com/owner/repo")
            self.assertEqual(len(result), 0)
        finally:
            req.get = original_get


if __name__ == '__main__':
    unittest.main()