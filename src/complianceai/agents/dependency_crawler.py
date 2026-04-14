"""Dependency Crawler - Resolves full dependency trees using package registries."""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any, Set, Tuple
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class DependencyCrawler:
    """Agent responsible for crawling dependency trees from package registries."""
    
    def __init__(self, max_depth: int = 5):
        """Initialize the Dependency Crawler.
        
        Args:
            max_depth: Maximum recursion depth to prevent infinite crawling
        """
        self.max_depth = max_depth
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def crawl_dependencies(self, packages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Crawl dependencies recursively starting from the given packages.
        
        Args:
            packages: List of dictionaries with 'name' and 'version' keys
            
        Returns:
            Dictionary representing the dependency tree
        """
        # Initialize the result dictionary and visited set
        dependency_tree = {}
        visited: Set[Tuple[str, str]] = set()  # (name, version) tuples
        
        # Create tasks for initial packages
        tasks = []
        for pkg in packages:
            name = pkg.get('name')
            version = pkg.get('version')
            if name:
                # root depth will be 1 in output
                task = self._crawl_package(name, version, 1, dependency_tree, visited)
                tasks.append(task)
        
        # Wait for all initial crawling tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return dependency_tree
    
    async def _crawl_package(self, name: str, version: str, depth: int, 
                           tree: Dict[str, Any], visited: Set[Tuple[str, str]]) -> None:
        """Recursively crawl a package and its dependencies.
        
        Args:
            name: Package name
            version: Package version (can be None)
            depth: Current depth in the dependency tree
            tree: The dependency tree being built
            visited: Set of already visited (name, version) tuples
        """
        # Check depth limit
        if depth > self.max_depth:
            logger.warning(f"Maximum depth exceeded for {name}@{version}")
            return
        
        # Create a unique identifier for this package version
        pkg_key = (name, version or "unknown")
        
        # Skip if already visited
        if pkg_key in visited:
            logger.debug(f"Skipping already visited package: {name}@{version}")
            return
        
        # Mark as visited
        visited.add(pkg_key)
        
        # Fetch package information from the appropriate registry
        try:
            package_info = await self._fetch_package_info(name, version)
        except Exception as e:
            logger.error(f"Failed to fetch info for {name}@{version}: {e}")
            # Still add the package to the tree even if we couldn't fetch details
            package_info = {
                "version": version,
                "license": None,
                "dependencies": [],
                "classifiers": [],
                "home_page": None,
                "project_urls": {},
                "license_expression": None,
            }
        
        # Normalize dependencies to a list of names for the output
        dep_tuples = package_info.get("dependencies", [])
        dep_names = [d[0] for d in dep_tuples]
        # Add package to the tree
        tree[name] = {
            "version": package_info.get("version", version),
            "license": package_info.get("license"),
            "dependencies": dep_names,
            "depth": depth,
            "classifiers": package_info.get("classifiers", []),
            "home_page": package_info.get("home_page"),
            "project_urls": package_info.get("project_urls", {}),
            "license_expression": package_info.get("license_expression"),
        }
        
        # Recursively crawl dependencies
        dependencies = package_info.get("dependencies", [])
        if dependencies and depth < self.max_depth:
            tasks = []
            for dep_name, dep_version in dependencies:
                task = self._crawl_package(dep_name, dep_version, depth + 1, tree, visited)
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _fetch_package_info(self, name: str, version: str) -> Dict[str, Any]:
        """Fetch package information from the appropriate registry.
        
        Args:
            name: Package name
            version: Package version (can be None)
            
        Returns:
            Dictionary with package information including dependencies
        """
        # Determine if this is likely a Python or JavaScript package
        # Heuristic: JavaScript packages often start with @ or have hyphens
        # Python packages typically use underscores, dots, or just alphanumeric
        is_js_package = name.startswith('@') or '-' in name
        
        if is_js_package:
            return await self._fetch_npm_package_info(name, version)
        else:
            return await self._fetch_pypi_package_info(name, version)
    
    def _clean_package_name(self, name: str) -> str:
        """Clean package name by removing version specifiers and extras.
        
        Examples:
            - "anyio<4,>=3.5.0" -> "anyio"
            - "requests>=2.0.0" -> "requests"
            - "package[extra]>=1.0" -> "package"
            - "importlib-metadata; python_version<3.8" -> "importlib-metadata"
        """
        import re
        cleaned = re.split(r'[<>=!~;\[,]', name)[0]
        cleaned = cleaned.strip()
        return cleaned
    
    def _extract_license_from_classifiers(self, classifiers: list) -> str:
        """Extract license from PyPI classifiers.
        
        Args:
            classifiers: List of classifier strings from PyPI
            
        Returns:
            License string or None
        """
        if not classifiers:
            return None
        
        for classifier in classifiers:
            classifier = classifier.lower()
            if 'license' in classifier or 'osi approved' in classifier:
                # Map classifier patterns to license names
                mappings = {
                    'mit license': 'MIT',
                    'apache': 'Apache-2.0',
                    'bsd 3-clause': 'BSD-3-Clause',
                    'bsd 2-clause': 'BSD-2-Clause',
                    'gnu general public license v3': 'GPL-3.0',
                    'gnu general public license v2': 'GPL-2.0',
                    'gnu lesser general public license': 'LGPL-3.0',
                    'mozilla public license': 'MPL-2.0',
                    'isc license': 'ISC',
                    'python software foundation': 'PSF-2.0',
                    'zlib license': 'Zlib',
                    'boost software license': 'BSL-1.0',
                    'artistic license': 'Artistic-2.0',
                    'eclipse public license': 'EPL-2.0',
                }
                for pattern, license in mappings.items():
                    if pattern in classifier:
                        return license
        return None
    
    def _extract_license_from_classifiers(self, classifiers: list) -> str:
        """Extract license from PyPI classifiers.
        
        Args:
            classifiers: List of classifier strings from PyPI
            
        Returns:
            License string or None
        """
        if not classifiers:
            return None
        
        for classifier in classifiers:
            classifier = classifier.lower()
            if 'license' in classifier or 'osi approved' in classifier:
                mappings = {
                    'mit license': 'MIT',
                    'apache': 'Apache-2.0',
                    'bsd 3-clause': 'BSD-3-Clause',
                    'bsd 2-clause': 'BSD-2-Clause',
                    'gnu general public license v3': 'GPL-3.0',
                    'gnu general public license v2': 'GPL-2.0',
                    'gnu lesser general public license': 'LGPL-3.0',
                    'mozilla public license': 'MPL-2.0',
                    'isc license': 'ISC',
                    'python software foundation': 'PSF-2.0',
                    'zlib license': 'Zlib',
                    'boost software license': 'BSL-1.0',
                    'artistic license': 'Artistic-2.0',
                    'eclipse public license': 'EPL-2.0',
                }
                for pattern, license in mappings.items():
                    if pattern in classifier:
                        return license
        return None
    
    def _clean_package_name(self, name: str) -> str:
        """Clean package name by removing version specifiers and extras."""
        import re
        cleaned = re.split(r'[<>=!~;\[,]', name)[0]
        cleaned = cleaned.strip()
        return cleaned
    
    async def _fetch_pypi_package_info(self, name: str, version: str) -> Dict[str, Any]:
        """Fetch package information from PyPI.
        
        Args:
            name: Package name
            version: Package version (can be None for latest)
            
        Returns:
            Dictionary with package information
        """
        session = await self._get_session()
        
        # Build the URL
        if version:
            url = f"https://pypi.org/pypi/{quote_plus(name)}/{quote_plus(version)}/json"
        else:
            url = f"https://pypi.org/pypi/{quote_plus(name)}/json"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    info = data.get("info", {})
                    
                    # Extract dependencies from requires_dist or fallback to empty list
                    requires_dist = info.get("requires_dist", []) or []
                    dependencies = []
                    
                    for dep in requires_dist:
                        if dep:
                            # Clean the package name - remove version specifiers
                            dep_name = self._clean_package_name(dep)
                            # Try to extract version constraint from parentheses if present
                            version_constraint = None
                            if '(' in dep and ')' in dep:
                                start = dep.find('(')
                                end = dep.find(')')
                                if start != -1 and end != -1:
                                    version_constraint = dep[start+1:end]
                            
                            dependencies.append((dep_name, version_constraint))
                    
                    # Extract license from three sources in priority order:
                    # 1. license field directly
                    # 2. license_expression field (newer PyPI field with SPDX)
                    # 3. classifiers (look for "License ::" prefix)
                    raw_license = info.get("license")
                    if not raw_license:
                        # Try license_expression field
                        raw_license = info.get("license_expression")
                    if not raw_license:
                        # Try classifiers - look for "License ::" prefix
                        raw_license = self._extract_license_from_classifiers(info.get("classifiers", []))
                    
                    return {
                        "version": info.get("version"),
                        "license": raw_license,
                        "classifiers": info.get("classifiers", []),
                        "home_page": info.get("home_page"),
                        "project_urls": info.get("project_urls", {}),
                        "license_expression": info.get("license_expression"),
                        "dependencies": dependencies
                    }
                else:
                    logger.warning(f"PyPI returned status {response.status} for {name}")
                    return {
                        "version": version,
                        "license": None,
                        "classifiers": [],
                        "home_page": None,
                        "project_urls": {},
                        "license_expression": None,
                        "dependencies": []
                    }
        except Exception as e:
            logger.error(f"Error fetching PyPI package {name}: {e}")
            return {
                "version": version,
                "license": None,
                "classifiers": [],
                "home_page": None,
                "project_urls": {},
                "license_expression": None,
                "dependencies": []
            }
    
    async def _fetch_npm_package_info(self, name: str, version: str) -> Dict[str, Any]:
        """Fetch package information from npm registry.
        
        Args:
            name: Package name
            version: Package version (can be None for latest)
            
        Returns:
            Dictionary with package information
        """
        session = await self._get_session()
        
        # Build the URL
        if version:
            url = f"https://registry.npmjs.org/{quote_plus(name)}/{quote_plus(version)}"
        else:
            url = f"https://registry.npmjs.org/{quote_plus(name)}"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract dependencies from the package data
                    dependencies = []
                    
                    # Check regular dependencies
                    deps = data.get("dependencies", {})
                    for dep_name, dep_version in deps.items():
                        dependencies.append((dep_name, dep_version))
                    
                    # Check peer dependencies (sometimes important)
                    peer_deps = data.get("peerDependencies", {})
                    for dep_name, dep_version in peer_deps.items():
                        dependencies.append((dep_name, dep_version))
                    
                    return {
                        "version": data.get("version"),
                        "license": data.get("license"),
                        "classifiers": [],
                        "dependencies": dependencies
                    }
                else:
                    logger.warning(f"NPM returned status {response.status} for {name}")
                    return {
                        "version": version,
                        "license": None,
                        "classifiers": [],
                        "dependencies": []
                    }
        except Exception as e:
            logger.error(f"Error fetching NPM package {name}: {e}")
            return {
                "version": version,
                "license": None,
                "classifiers": [],
                "dependencies": []
            }
