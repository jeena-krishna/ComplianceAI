"""Tests for the License Agent."""

import unittest
import sys
import os

# Add src to path so we can import complianceai
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from complianceai.agents.license_agent import LicenseAgent


class TestLicenseAgent(unittest.TestCase):
    """Test cases for the LicenseAgent class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = LicenseAgent()
    
    def test_init(self):
        """Test that the agent initializes correctly."""
        self.assertIsInstance(self.agent, LicenseAgent)
        self.assertIsInstance(self.agent._license_lookup, dict)
        self.assertIsInstance(self.agent.SPDX_LICENSE_MAP, dict)
    
    def test_identify_licenses_empty_input(self):
        """Test identifying licenses with empty input."""
        result = self.agent.identify_licenses([])
        self.assertEqual(result, {})
    
    def test_identify_licenses_with_license(self):
        """Test identifying licenses for packages that have license info."""
        dependencies = [
            {"name": "test-package", "version": "1.0.0", "license": "MIT"},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result["test-package"]["name"], "test-package")
        self.assertEqual(result["test-package"]["version"], "1.0.0")
        self.assertEqual(result["test-package"]["license"], "MIT")
        self.assertEqual(result["test-package"]["license_source"], "package")
    
    def test_identify_licenses_without_license(self):
        """Test identifying licenses for packages without license info."""
        dependencies = [
            {"name": "test-package", "version": "1.0.0"},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[list(result.keys())[0]]["license"], "Unknown")
        self.assertEqual(result[list(result.keys())[0]]["license_source"], "missing")
    
    def test_identify_licenses_preserves_name_and_version(self):
        """Test that name and version are preserved."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0"},
            {"name": "requests", "version": "2.28.0"},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        
        self.assertEqual(result["numpy"]["name"], "numpy")
        self.assertEqual(result["numpy"]["version"], "1.24.0")
        self.assertEqual(result["requests"]["name"], "requests")
        self.assertEqual(result["requests"]["version"], "2.28.0")
    
    def test_normalize_license_mit(self):
        """Test normalizing MIT license."""
        self.assertEqual(self.agent._normalize_license("MIT"), "MIT")
        self.assertEqual(self.agent._normalize_license("mit"), "MIT")
        self.assertEqual(self.agent._normalize_license("MIT License"), "MIT")
        self.assertEqual(self.agent._normalize_license("Expat"), "MIT")
    
    def test_normalize_license_apache(self):
        """Test normalizing Apache license."""
        self.assertEqual(self.agent._normalize_license("Apache-2.0"), "Apache-2.0")
        self.assertEqual(self.agent._normalize_license("apache"), "Apache-2.0")
        self.assertEqual(self.agent._normalize_license("Apache License 2.0"), "Apache-2.0")
    
    def test_normalize_license_gpl(self):
        """Test normalizing GPL licenses."""
        self.assertEqual(self.agent._normalize_license("GPL-3.0"), "GPL-3.0")
        self.assertEqual(self.agent._normalize_license("gpl-3.0"), "GPL-3.0")
        self.assertEqual(self.agent._normalize_license("GPL-2.0"), "GPL-2.0")
        self.assertEqual(self.agent._normalize_license("GNU General Public License v3 (GPL-3.0)"), "GPL-3.0")
    
    def test_normalize_license_bsd(self):
        """Test normalizing BSD licenses."""
        self.assertEqual(self.agent._normalize_license("BSD-3-Clause"), "BSD-3-Clause")
        self.assertEqual(self.agent._normalize_license("bsd-3-clause"), "BSD-3-Clause")
        self.assertEqual(self.agent._normalize_license("BSD-2-Clause"), "BSD-2-Clause")
        self.assertEqual(self.agent._normalize_license("Simplified BSD"), "BSD-2-Clause")
    
    def test_normalize_license_isc(self):
        """Test normalizing ISC license."""
        self.assertEqual(self.agent._normalize_license("ISC"), "ISC")
        self.assertEqual(self.agent._normalize_license("isc"), "ISC")
    
    def test_normalize_license_mpl(self):
        """Test normalizing MPL license."""
        self.assertEqual(self.agent._normalize_license("MPL-2.0"), "MPL-2.0")
        self.assertEqual(self.agent._normalize_license("Mozilla Public License 2.0"), "MPL-2.0")
    
    def test_normalize_license_lgpl(self):
        """Test normalizing LGPL licenses."""
        self.assertEqual(self.agent._normalize_license("LGPL-2.1"), "LGPL-2.1")
        self.assertEqual(self.agent._normalize_license("LGPL-3.0"), "LGPL-3.0")
    
    def test_normalize_license_agpl(self):
        """Test normalizing AGPL license."""
        self.assertEqual(self.agent._normalize_license("AGPL-3.0"), "AGPL-3.0")
        self.assertEqual(self.agent._normalize_license("agpl"), "AGPL-3.0")
    
    def test_normalize_license_zlib(self):
        """Test normalizing zlib license."""
        self.assertEqual(self.agent._normalize_license("zlib"), "Zlib")
        self.assertEqual(self.agent._normalize_license("Zlib"), "Zlib")
    
    def test_normalize_license_psf(self):
        """Test normalizing PSF license."""
        self.assertEqual(self.agent._normalize_license("PSF-2.0"), "PSF-2.0")
        self.assertEqual(self.agent._normalize_license("Python Software Foundation License"), "PSF-2.0")
    
    def test_normalize_license_unlicense(self):
        """Test normalizing Unlicense."""
        self.assertEqual(self.agent._normalize_license("Unlicense"), "Unlicense")
        self.assertEqual(self.agent._normalize_license("public domain"), "CC0-1.0")
    
    def test_normalize_license_cc0(self):
        """Test normalizing CC0 license."""
        self.assertEqual(self.agent._normalize_license("CC0-1.0"), "CC0-1.0")
        self.assertEqual(self.agent._normalize_license("Public Domain"), "CC0-1.0")
    
    def test_normalize_license_unknown(self):
        """Test normalizing unknown license."""
        self.assertEqual(self.agent._normalize_license(""), "Unknown")
        self.assertEqual(self.agent._normalize_license(None), "Unknown")
        self.assertEqual(self.agent._normalize_license("Some Weird License XYZ"), "Unknown")
        self.assertEqual(self.agent._normalize_license(" Proprietary "), "Unknown")
    
    def test_normalize_license_already_valid(self):
        """Test that valid SPDX identifiers are preserved."""
        valid_licenses = [
            "MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "BSD-3-Clause",
            "BSD-2-Clause", "ISC", "MPL-2.0", "LGPL-2.1", "LGPL-3.0",
            "AGPL-3.0", "Zlib", "PSF-2.0", "Unlicense", "CC0-1.0",
            "CC-BY-4.0", "CC-BY-SA-4.0"
        ]
        
        for license_str in valid_licenses:
            with self.subTest(license=license_str):
                result = self.agent._normalize_license(license_str)
                self.assertEqual(result, license_str)
    
    def test_extract_spdx(self):
        """Test extracting SPDX from license strings."""
        # Test direct matches
        self.assertEqual(self.agent._extract_spdx("MIT"), "MIT")
        self.assertEqual(self.agent._extract_spdx("GPL-3.0"), "GPL-3.0")
        self.assertEqual(self.agent._extract_spdx("BSD-3-Clause"), "BSD-3-Clause")
        
        # Test non-matching strings (the lookup handles most of these)
        self.assertIsNone(self.agent._extract_spdx("MIT License"))
        self.assertIsNone(self.agent._extract_spdx("Apache License 2.0"))
        self.assertIsNone(self.agent._extract_spdx("XYZ Unknown"))
    
    def test_get_license_source(self):
        """Test determining license source."""
        # From package metadata (exact match)
        self.assertEqual(self.agent._get_license_source("MIT", "MIT"), "package")
        
        # Missing license
        self.assertEqual(self.agent._get_license_source(None, "Unknown"), "missing")
        self.assertEqual(self.agent._get_license_source("", "Unknown"), "missing")
        
        # Inferred (normalized from non-standard)
        self.assertEqual(self.agent._get_license_source("MIT License", "MIT"), "inferred")
        self.assertEqual(self.agent._get_license_source("Apache 2.0", "Apache-2.0"), "inferred")
    
    def test_identify_licenses_multiple_packages(self):
        """Test identifying licenses for multiple packages."""
        dependencies = [
            {"name": "numpy", "version": "1.24.0", "license": "BSD-3-Clause"},
            {"name": "requests", "version": "2.28.0", "license": "Apache-2.0"},
            {"name": "unknownpkg", "version": "2.0.0"},  # No license - package name not known
            {"name": "flask", "version": "2.0.0"},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        
        self.assertEqual(len(result), 4)
        
        # Check each package by key
        self.assertEqual(result["numpy"]["license"], "BSD-3-Clause")
        self.assertEqual(result["requests"]["license"], "Apache-2.0")
        # unknownpkg - no license info, not in known packages
        self.assertEqual(result["unknownpkg"]["license"], "Unknown")
        # flask is guessed from package name database
        self.assertEqual(result["flask"]["license"], "BSD-3-Clause")
    
    def test_identify_licenses_preserves_original(self):
        """Test that original license is preserved for reference."""
        dependencies = [
            {"name": "test-package", "version": "1.0.0", "license": "MIT License"},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        
        self.assertEqual(result["test-package"]["original_license"], "MIT License")
        self.assertEqual(result["test-package"]["license"], "MIT")


class TestGitHubLicenseDetection(unittest.TestCase):
    """Test cases for GitHub license fallback."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = LicenseAgent()

    def test_detect_license_from_content_mit(self):
        """Test detecting MIT license from content."""
        content = "MIT License\n\nPermission is hereby granted..."
        result = self.agent._detect_license_from_content(content)
        self.assertEqual(result, "MIT")

    def test_detect_license_from_content_apache(self):
        """Test detecting Apache license from content."""
        content = "Apache License, Version 2.0\n\nLicensed under the Apache License..."
        result = self.agent._detect_license_from_content(content)
        self.assertEqual(result, "Apache-2.0")

    def test_detect_license_from_content_gpl(self):
        """Test detecting GPL license from content."""
        content = "GNU General Public License v3"
        result = self.agent._detect_license_from_content(content)
        self.assertEqual(result, "GPL-3.0")

    def test_detect_license_from_content_bsd(self):
        """Test detecting BSD license from content."""
        content = "BSD 3-Clause License"
        result = self.agent._detect_license_from_content(content)
        self.assertEqual(result, "BSD-3-Clause")

    def test_detect_license_from_content_unknown(self):
        """Test unknown content returns Unknown."""
        content = "Some random text without license info"
        result = self.agent._detect_license_from_content(content)
        self.assertEqual(result, "Unknown")

    def test_lookup_github_license_none(self):
        """Test invalid GitHub URL returns Unknown."""
        result = self.agent._lookup_github_license("https://example.com/notgithub")
        self.assertEqual(result, "Unknown")

    def test_identify_licenses_with_github_fallback(self):
        """Test GitHub fallback when PyPI license is unknown."""
        dependencies = [
            {'name': 'unknown-pkg', 'license': None, 'home_page': 'https://github.com owner/repo'},
        ]
        
        result = self.agent.identify_licenses(dependencies)
        self.assertIsInstance(result, dict)
        self.assertIn('unknown-pkg', result)


if __name__ == '__main__':
    unittest.main()