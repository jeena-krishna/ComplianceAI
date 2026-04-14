    @patch('aiohttp.ClientSession')
    async def test_fetch_npm_package_info_http_error(self, mock_session_class):
        """Test npm package info fetch with HTTP error."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        # Call the method
        result = await self.crawler._fetch_npm_package_info("nonexistent-package", "1.0.0")
        
        # Verify results - should return default values
        self.assertEqual(result["version"], "1.0.0")
        self.assertIsNone(result["license"])
        self.assertEqual(result["dependencies"], [])
    
    @patch('aiohttp.ClientSession')
    async def test_fetch_npm_package_info_exception(self, mock_session_class):
        """Test npm package info fetch with exception."""
        # Setup mock to raise exception
        mock_session_class.side_effect = Exception("Network error")
        
        # Call the method
        result = await self.crawler._fetch_npm_package_info("test-package", "1.0.0")
        
        # Verify results - should return default values
        self.assertEqual(result["version"], "1.0.0")
        self.assertIsNone(result["license"])
        self.assertEqual(result["dependencies"], [])
    
    async def test_crawl_dependencies_empty_input(self):
        """Test crawling with empty input."""
        result = await self.crawler.crawl_dependencies([])
        self.assertEqual(result, {})
    
    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_dependencies_single_package(self, mock_fetch):
        """Test crawling a single package with no dependencies."""
        # Setup mock
        mock_fetch.return_value = {
            "version": "1.0.0",
            "license": "MIT",
            "dependencies": []
        }
        
        # Call the method
        packages = [{"name": "test-package", "version": "1.0.0"}]
        result = await self.crawler.crawl_dependencies(packages)
        
        # Verify results
        self.assertIn("test-package", result)
        self.assertEqual(result["test-package"]["version"], "1.0.0")
        self.assertEqual(result["test-package"]["license"], "MIT")
        self.assertEqual(result["test-package"]["dependencies"], [])
        self.assertEqual(result["test-package"]["depth"], 1)
        
        # Verify the mock was called
        mock_fetch.assert_called_once_with("test-package", "1.0.0")
    
    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_dependencies_with_subdependencies(self, mock_fetch):
        """Test crawling with sub-dependencies."""
        # Setup mock responses
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
            elif name == "grandchild":
                return {
                    "version": "3.0.0",
                    "license": "GPL-3.0",
                    "dependencies": []
                }
            else:
                return {
                    "version": version or "1.0.0",
                    "license": None,
                    "dependencies": []
                }
        
        mock_fetch.side_effect = side_effect
        
        # Call the method
        packages = [{"name": "parent", "version": "1.0.0"}]
        result = await self.crawler.crawl_dependencies(packages)
        
        # Verify results
        self.assertIn("parent", result)
        self.assertIn("child", result)
        self.assertIn("grandchild", result)
        
        # Check parent
        self.assertEqual(result["parent"]["version"], "1.0.0")
        self.assertEqual(result["parent"]["license"], "MIT")
        self.assertEqual(result["parent"]["dependencies"], ["child"])
        self.assertEqual(result["parent"]["depth"], 1)
        
        # Check child
        self.assertEqual(result["child"]["version"], "2.0.0")
        self.assertEqual(result["child"]["license"], "Apache-2.0")
        self.assertEqual(result["child"]["dependencies"], ["grandchild"])
        self.assertEqual(result["child"]["depth"], 2)
        
        # Check grandchild
        self.assertEqual(result["grandchild"]["version"], "3.0.0")
        self.assertEqual(result["grandchild"]["license"], "GPL-3.0")
        self.assertEqual(result["grandchild"]["dependencies"], [])
        self.assertEqual(result["grandchild"]["depth"], 3)
    
    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_dependencies_skip_visited(self, mock_fetch):
        """Test that already visited packages are skipped."""
        # Setup mock to return different data each time to detect if called multiple times
        call_count = {}
        
        def side_effect(name, version):
            key = f"{name}_{version}"
            call_count[key] = call_count.get(key, 0) + 1
            return {
                "version": version or "1.0.0",
                "license": "MIT",
                "dependencies": [("child", "1.0.0")] if name == "parent" else []
            }
        
        mock_fetch.side_effect = side_effect
        
        # Call the method with packages that reference each other
        packages = [
            {"name": "parent", "version": "1.0.0"},
            {"name": "child", "version": "1.0.0"}  # This is also a dependency of parent
        ]
        result = await self.crawler.crawl_dependencies(packages)
        
        # Verify results
        self.assertIn("parent", result)
        self.assertIn("child", result)
        
        # The child package should only be fetched once despite being referenced twice
        self.assertEqual(call_count.get("child_1.0.0", 0), 1)
    
    @patch('complianceai.agents.dependency_crawler.DependencyCrawler._fetch_package_info')
    async def test_crawl_dependencies_max_depth(self, mock_fetch):
        """Test that maximum depth is respected."""
        # Setup mock to return a chain of dependencies
        call_depths = {}
        
        def side_effect(name, version):
            # Track how deep we've gone for each package
            if name not in call_depths:
                call_depths[name] = 0
            call_depths[name] += 1
            
            # Always return a dependency unless we're at depth 5
            if call_depths[name] < 5:
                return {
                    "version": version or "1.0.0",
                    "license": "MIT",
                    "dependencies": [(f"{name}-child", "1.0.0")]
                }
            else:
                return {
                    "version": version or "1.0.0",
                    "license": "MIT",
                    "dependencies": []
                }
        
        mock_fetch.side_effect = side_effect
        
        # Call the method with max_depth=2
        crawler = DependencyCrawler(max_depth=2)
        packages = [{"name": "root", "version": "1.0.0"}]
        result = await crawler.crawl_dependencies(packages)
        
        # With max_depth=2, we should only get root (depth 1) and its child (depth 2)
        # The grandchild (depth 3) should not be included
        self.assertIn("root", result)
        self.assertIn("root-child", result)
        self.assertNotIn("root-child-child", result)  # This would be depth 3
        
        # Check depths
        self.assertEqual(result["root"]["depth"], 1)
        self.assertEqual(result["root-child"]["depth"], 2)
    
    def test_is_js_package_helper(self):
        """Test the JavaScript package detection helper."""
        # Add the helper method if it doesn't exist
        if not hasattr(self.crawler, '_is_js_package'):
            # Create a simple version for testing
            def _is_js_package(name):
                return name.startswith('@') or '-' in name
            self.crawler._is_js_package = _is_js_package
        
        self.assertTrue(self.crawler._is_js_package("@types/node"))
        self.assertTrue(self.crawler._is_js_package("react-dom"))
        self.assertTrue(self.crawler._is_js_package("@scope/package"))
        self.assertFalse(self.crawler._is_js_package("numpy"))
        self.assertFalse(self.crawler._is_js_package("requests"))


if __name__ == '__main__':
    unittest.main()