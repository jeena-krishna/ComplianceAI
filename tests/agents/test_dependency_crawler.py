"""Tests for the Dependency Crawler Agent."""

import asyncio
import json
import sys
import os
import unittest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from complianceai.agents.dependency_crawler import DependencyCrawler


class TestDependencyCrawlerAsync(unittest.IsolatedAsyncioTestCase):
    """Test async cases for DependencyCrawler."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.crawler = DependencyCrawler()

    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_single_package(self, mock_fetch):
        """Test crawling a single package."""
        mock_fetch.return_value = {
            "version": "1.0.0",
            "license": "MIT",
            "dependencies": []
        }

        packages = [{"name": "test-package", "version": "1.0.0"}]
        result = await self.crawler.crawl_dependencies(packages)

        self.assertIn("test-package", result)
        self.assertEqual(result["test-package"]["version"], "1.0.0")
        self.assertEqual(result["test-package"]["license"], "MIT")
        self.assertEqual(result["test-package"]["dependencies"], [])
        self.assertEqual(result["test-package"]["depth"], 1)

        mock_fetch.assert_called_once_with("test-package", "1.0.0")

    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_dependencies_with_subdependencies(self, mock_fetch):
        """Test crawling with sub-dependencies."""
        def side_effect(name, version):
            if name == "parent":
                return {
                    "version": "1.0.0",
                    "license": "MIT",
                    "dependencies": [("child", "2.0.0")]
                }
            elif name == "child":
                return {
                    "version": "2.0.0",
                    "license": "Apache-2.0",
                    "dependencies": [("grandchild", "3.0.0")]
                }
            else:
                return {
                    "version": version or "1.0.0",
                    "license": None,
                    "dependencies": []
                }

        mock_fetch.side_effect = side_effect

        packages = [{"name": "parent", "version": "1.0.0"}]
        result = await self.crawler.crawl_dependencies(packages)

        self.assertIn("parent", result)
        self.assertIn("child", result)
        self.assertIn("grandchild", result)

        self.assertEqual(result["parent"]["version"], "1.0.0")
        self.assertEqual(result["parent"]["license"], "MIT")
        self.assertEqual(result["parent"]["dependencies"], ["child"])
        self.assertEqual(result["parent"]["depth"], 1)

        self.assertEqual(result["child"]["version"], "2.0.0")
        self.assertEqual(result["child"]["license"], "Apache-2.0")
        self.assertEqual(result["child"]["dependencies"], ["grandchild"])
        self.assertEqual(result["child"]["depth"], 2)

        self.assertEqual(result["grandchild"]["depth"], 3)

    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_respects_max_depth(self, mock_fetch):
        """Test that max_depth is respected."""
        def side_effect(name, version):
            return {
                "version": "1.0.0",
                "license": "MIT",
                "dependencies": [("child", "1.0.0")]
            }

        mock_fetch.side_effect = side_effect

        packages = [{"name": "root", "version": "1.0.0"}]
        result = await self.crawler.crawl_dependencies(packages)

        self.assertIn("root", result)
        self.assertIn("child", result)
        self.assertEqual(result["root"]["depth"], 1)
        self.assertEqual(result["child"]["depth"], 2)

    @patch('aiohttp.ClientSession')
    async def test_fetch_npm_package_info_http_error(self, mock_session_class):
        """Test npm package info fetch with HTTP error."""
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session

        result = await self.crawler._fetch_npm_package_info("nonexistent-package", "1.0.0")

        self.assertEqual(result["version"], "1.0.0")
        self.assertIsNone(result["license"])
        self.assertEqual(result["dependencies"], [])

    @patch('aiohttp.ClientSession')
    async def test_fetch_npm_package_info_exception(self, mock_session_class):
        """Test npm package info fetch with exception."""
        mock_session_class.side_effect = Exception("Network error")

        result = await self.crawler._fetch_npm_package_info("test-package", "1.0.0")

        self.assertEqual(result["version"], "1.0.0")
        self.assertIsNone(result["license"])
        self.assertEqual(result["dependencies"], [])


if __name__ == '__main__':
    unittest.main()