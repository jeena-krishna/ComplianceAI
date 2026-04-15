"""Dependency Agent - Parses dependency files and extracts package information."""

import json
import os
import re
import zipfile
import io
import tempfile
import requests
from typing import Dict, List, Any, Union
from urllib.parse import urlparse


class DependencyAgent:
    """Agent responsible for parsing dependency files and extracting package information."""
    
    def __init__(self):
        """Initialize the Dependency Agent."""
        self.github_token = None  # Not needed anymore - zip approach doesn't hit API limits
        
        # Regex patterns for parsing different dependency formats
        self.requirements_pattern = re.compile(
            r'^\s*([a-zA-Z0-9][a-zA-Z0-9._-]*)\s*([=<>!~]+.*)?\s*$'
        )
    
    def parse_input(self, input_data: Union[str, Dict]) -> List[Dict[str, Any]]:
        """Parse input data and extract dependencies.
        
        Args:
            input_data: Either a file path, raw text, or GitHub URL
            
        Returns:
            List of dictionaries with package name and version
        """
        # Check if it's a file path
        if isinstance(input_data, str) and os.path.isfile(input_data):
            return self._parse_file(input_data)
        
        # Check if it's a GitHub URL
        if isinstance(input_data, str) and self._is_github_url(input_data):
            return self._parse_github_url(input_data)
        
        # Otherwise treat as raw text
        return self._parse_raw_text(input_data)
    
    def _is_github_url(self, url: str) -> bool:
        """Check if the input is a GitHub URL."""
        try:
            parsed = urlparse(url)
            # Handle github.com and www.github.com
            hostname = parsed.netloc.lower()
            return ('github.com' in hostname) and len(parsed.path.strip('/').split('/')) >= 2
        except Exception:
            return False
    
    def _parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a dependency file based on its extension/name."""
        file_name = os.path.basename(file_path)
        
        if file_name == 'requirements.txt':
            return self._parse_requirements_txt(file_path)
        elif file_name == 'package.json':
            return self._parse_package_json(file_path)
        elif file_name in ['Pipfile', 'setup.py', 'poetry.lock', 'pom.xml', 'build.gradle']:
            # TODO: Implement parsing for these file types
            return []
        else:
            # Try to parse as raw text
            with open(file_path, 'r') as f:
                content = f.read()
            return self._parse_raw_text(content)
    
    def _parse_requirements_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a requirements.txt file."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Remove inline comments
                    if ' #' in line:
                        line = line.split(' #')[0].strip()
                    
                    # Handle -r (recursive) and -e (editable) flags
                    if line.startswith('-r ') or line.startswith('--requirement ') or \
                       line.startswith('-e ') or line.startswith('--editable ') or \
                       line.startswith('-c ') or line.startswith('--constraint '):
                        # TODO: Handle recursive requirements
                        continue
                    
                    # Parse package specification
                    dep = self._parse_package_spec(line)
                    if dep:
                        dependencies.append(dep)
        except Exception as e:
            # In case of file reading error, return empty list
            pass
        
        return dependencies
    
    def _parse_package_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a package.json file."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract from dependencies
            deps = data.get('dependencies', {})
            for name, version in deps.items():
                dependencies.append({
                    "name": name,
                    "version": version if version != "*" else None
                })
            
            # Extract from devDependencies
            dev_deps = data.get('devDependencies', {})
            for name, version in dev_deps.items():
                dependencies.append({
                    "name": name,
                    "version": version if version != "*" else None
                })
                
        except Exception as e:
            # In case of JSON parsing error, return empty list
            pass
        
        return dependencies
    
    def _parse_raw_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse raw text input looking for dependency specifications."""
        dependencies = []
        
        # Try to parse as JSON first (could be package.json content)
        try:
            data = json.loads(text)
            if isinstance(data, dict) and ('dependencies' in data or 'devDependencies' in data):
                # Looks like package.json content
                deps = data.get('dependencies', {})
                for name, version in deps.items():
                    dependencies.append({
                        "name": name,
                        "version": version if version != "*" else None
                    })
                
                dev_deps = data.get('devDependencies', {})
                for name, version in dev_deps.items():
                    dependencies.append({
                        "name": name,
                        "version": version if version != "*" else None
                    })
                return dependencies
        except json.JSONDecodeError:
            # Not JSON, treat as requirements.txt style
            pass
        
        # Parse line by line as requirements.txt
        for line in text.split('\n'):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
                
            dep = self._parse_package_spec(line)
            if dep:
                dependencies.append(dep)
        
        return dependencies
    
    def _parse_package_spec(self, spec: str) -> Dict[str, Any]:
        """Parse a package specification string."""
        # Handle various formats:
        # package==1.0.0
        # package>=1.0.0
        # package<=2.0.0
        # package>1.0.0
        # package<2.0.0
        # package~=1.0.0
        # package!=1.0.0
        # package
        # package@1.0.0 (npm style)
        # "package" (quoted string from setup.py)
        
        # Remove whitespace
        spec = spec.strip()
        
        # Strip quotes (common in setup.py: "package", 'package')
        if (spec.startswith('"') and spec.endswith('"')) or \
           (spec.startswith("'") and spec.endswith("'")):
            spec = spec[1:-1].strip()
        
        # Skip empty specs
        if not spec:
            return None
        
        # Handle @ syntax (common in npm/yarn) - this includes scoped packages like @types/node
        if '@' in spec:
            parts = spec.split('@', 1)
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else None
            # For scoped packages like @types/node, the name will be empty after split
            # so we need to handle that case
            if not name and len(parts) == 2 and parts[0].endswith('/'):
                # This is a scoped package like @types/node
                name = '@' + parts[0].rstrip('/')
                version = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            elif name:  # Regular package with @ syntax
                return {
                    "name": name,
                    "version": version if version else None
                }
            # If we got here with a scoped package, continue to return it below
        
        # Handle traditional specifiers
        match = self.requirements_pattern.match(spec)
        if match:
            name = match.group(1)
            version_spec = match.group(2)
            
            # Clean up the name (remove extras)
            name = name.strip()
            
            if not name:
                return None
            
            # Extract just the version number, stripping operators
            version = None
            if version_spec:
                # Remove whitespace and extract just the version part
                version_spec = version_spec.strip()
                # Handle cases like ==1.0.0, >=1.0.0, etc.
                # Extract the version number after the operator
                version_match = re.match(r'[=<>!~]+(.*)', version_spec)
                if version_match:
                    version = version_match.group(1).strip()
                    # Handle empty version
                    if not version:
                        version = None
            
            return {
                "name": name,
                "version": version
            }
        
        # If we have an @ syntax scoped package that wasn't handled above
        if spec.startswith('@') and '/' in spec:
            # This is a scoped package like @types/node or @scope@version
            if '@' in spec[1:]:  # Has version specifier
                parts = spec.split('@', 2)  # Split into [scope/name, version, ...]
                if len(parts) >= 2:
                    name = '@' + parts[0]
                    version = parts[1] if parts[1] else None
                    return {
                        "name": name,
                        "version": version if version else None
                    }
            else:  # Just a scoped package without version
                return {
                    "name": spec,
                    "version": None
                }
        
        return None
    
    def _parse_github_url(self, url: str) -> List[Dict[str, Any]]:
        """Parse a GitHub URL by downloading the entire repo as a zip.
        
        This approach:
        - Uses only 1 HTTP request (no rate limit issues)
        - Searches entire repo including subdirectories for monorepos
        - Supports all dependency file formats
        
        For monorepos:
        - Walks ALL subdirectories to find dependency files
        - Extracts dependencies from ALL pyproject.toml, setup.py, setup.cfg, etc.
        - Deduplicates by package name, keeping first version found
        
        Args:
            url: GitHub repository URL (e.g., https://github.com/user/repo)
            
        Returns:
            List of dependencies found in the repo's dependency files
            Also populates self._debug_info for UI display
        """
        self._debug_info = []
        
        # Extract owner/repo from URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return []
        
        owner = path_parts[0]
        repo_name = path_parts[1].replace('.git', '')
        
        self._debug_info.append(f"Fetching {owner}/{repo_name}...")
        
        # Try different branches
        branches = ['main', 'master', 'develop', 'dev']
        
        for branch in branches:
            zip_url = f"https://github.com/{owner}/{repo_name}/archive/refs/heads/{branch}.zip"
            
            try:
                response = requests.get(zip_url, timeout=60, allow_redirects=True)
                if response.status_code != 200:
                    continue
                
                self._debug_info.append(f"Downloaded branch: {branch}")
                    
                # Extract zip to temp folder
                with tempfile.TemporaryDirectory() as tmpdir:
                    z = zipfile.ZipFile(io.BytesIO(response.content))
                    z.extractall(tmpdir)
                    
                    # Find ALL dependency files recursively (including requirements*.txt pattern)
                    all_dependencies = []
                    found_files = []
                    
                    for root, dirs, files in os.walk(tmpdir):
                        # Calculate depth from root (after tmpdir/<repo>-<branch>/)
                        rel_path = root[len(tmpdir):].lstrip(os.sep)
                        depth = rel_path.count(os.sep) + (1 if rel_path else 0)
                        
                        # Skip hidden directories and common non-dep dirs
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', 'venv', '.git')]
                        
                        for filename in files:
                            # Check if it's a known dependency file pattern
                            is_dep_file = any([
                                'requirements' in filename.lower() and filename.endswith('.txt'),
                                filename == 'package.json',
                                filename == 'Pipfile',
                                filename == 'pyproject.toml',
                                filename == 'setup.py',
                                filename == 'setup.cfg',
                            ])
                            
                            if not is_dep_file:
                                continue
                            
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, tmpdir)
                            found_files.append(rel_path)
                            
                            try:
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                            except Exception:
                                continue
                            
                            
                            deps = []
                            deps_count = 0
                            
                            # Parse based on file type
                            if 'requirements' in filename.lower() and filename.endswith('.txt'):
                                deps = self._parse_raw_text(content)
                            elif filename == 'package.json':
                                deps = self._parse_package_json_string(content)
                            elif filename == 'pyproject.toml':
                                deps, deps_count = self._parse_pyproject_toml(content)
                            elif filename == 'setup.cfg':
                                deps = self._parse_setup_cfg(content)
                            elif filename == 'setup.py':
                                deps = self._parse_setup_py(content)
                            
                            if deps:
                                all_dependencies.extend(deps)
                                self._debug_info.append(f"  Found {rel_path}: {len(deps)} deps")
                            elif deps_count is not None:
                                # pyproject returned deps count but they may be empty
                                self._debug_info.append(f"  Found {rel_path}: {deps_count} deps (parsed)")
                            else:
                                self._debug_info.append(f"  Found {rel_path}: no parseable deps")
                    
                    if not found_files:
                        self._debug_info.append("  No dependency files found")
                    
                    # If we found dependencies, return them
                    if all_dependencies:
                        final_deps = self._deduplicate_dependencies(all_dependencies)
                        self._debug_info.append(f"Total unique deps: {len(final_deps)}")
                        return final_deps
                        
            except Exception as e:
                self._debug_info.append(f"Error: {str(e)}")
                continue
        
        self._debug_info.append("No dependencies found")
        return []
    
    @property
    def debug_info(self) -> List[str]:
        """Get debug info for UI display."""
        return getattr(self, '_debug_info', [])
    
    def _deduplicate_dependencies(self, deps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate dependencies, keeping first occurrence."""
        seen = set()
        unique = []
        for dep in deps:
            name = dep.get('name')
            if name and name not in seen:
                seen.add(name)
                unique.append(dep)
        return unique
    
    def _parse_pyproject_toml(self, content: str) -> tuple[List[Dict[str, Any]], int]:
        """Parse pyproject.toml and extract dependencies.
        
        Args:
            content: Raw TOML content
            
        Returns:
            Tuple of (dependencies list, raw deps count for debug)
        """
        dependencies = []
        deps_count = 0
        
        try:
            import tomli as tomllib
            data = tomllib.loads(content)
        except ImportError:
            import tomllib
            data = tomllib.loads(content)
        
        # Try PEP 621 format: project.dependencies
        project_deps = data.get('project', {}).get('dependencies', [])
        for dep in project_deps:
            parsed = self._parse_package_spec(dep)
            if parsed:
                dependencies.append(parsed)
        deps_count += len(project_deps)
        
        # Try Poetry format: tool.poetry.dependencies
        poetry_deps = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
        for name, version in poetry_deps.items():
            # Skip the python version constraint
            if name == 'python':
                continue
            # Handle version as string (e.g., "^1.0" or exact version)
            ver = str(version) if version else None
            dependencies.append({'name': name, 'version': ver})
        deps_count += len(poetry_deps)
        
        # Try optional-dependencies (extras)
        optional_deps = data.get('project', {}).get('optional-dependencies', {})
        for group_name, extras_dict in optional_deps.items():
            for dep in extras_dict:
                parsed = self._parse_package_spec(dep)
                if parsed:
                    dependencies.append(parsed)
        deps_count += sum(len(v) for v in optional_deps.values())
        
        # Try build-system.requires (usually pip, setuptools, wheel)
        build_requires = data.get('build-system', {}).get('requires', [])
        for dep in build_requires:
            parsed = self._parse_package_spec(dep)
            if parsed:
                dependencies.append(parsed)
        deps_count += len(build_requires)
        
        return dependencies, deps_count
    
    def _parse_setup_cfg(self, content: str) -> List[Dict[str, Any]]:
        """Parse setup.cfg and extract install_requires.
        
        Args:
            content: Raw INI content
            
        Returns:
            List of dependencies
        """
        import configparser
        dependencies = []
        
        try:
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # Parse [options] section
            if config.has_section('options'):
                if config.has_option('options', 'install_requires'):
                    install_requires = config.get('options', 'install_requires')
                    deps = self._parse_requirements_list(install_requires)
                    for dep in deps:
                        parsed = self._parse_package_spec(dep)
                        if parsed:
                            dependencies.append(parsed)
            
            # Parse [options.extras_require] section
            if config.has_section('options.extras_require'):
                for key in config.options('options.extras_require'):
                    extras = config.get('options.extras_require', key)
                    deps = self._parse_requirements_list(extras)
                    for dep in deps:
                        parsed = self._parse_package_spec(dep)
                        if parsed:
                            dependencies.append(parsed)
        except Exception:
            pass
        
        return dependencies
    
    def _parse_requirements_list(self, text: str) -> List[str]:
        """Parse a requirements list string into individual package specs.
        
        Handles:
        - comma-separated lists
        - multiline lists with backslash continuation
        - semicolon-separated (environment markers)
        
        Args:
            text: Requirements string
            
        Returns:
            List of individual package specifications
        """
        packages = []
        
        # Replace line continuations with spaces
        text = text.replace('\\\n', ' ').replace('\\\r\n', ' ')
        
        # Split by comma or semicolon (semicolons are usually markers)
        parts = re.split(r'[;,\n]', text)
        
        for part in parts:
            part = part.strip()
            # Skip empty parts and comments
            if part and not part.startswith('#'):
                # Remove any inline comments
                if '#' in part:
                    part = part.split('#')[0].strip()
                if part:
                    packages.append(part)
        
        return packages
    
    def _parse_setup_py(self, content: str) -> List[Dict[str, Any]]:
        """Parse setup.py and extract install_requires using regex.
        
        Handles:
        - Inline lists: install_requires = ["pkg1", "pkg2"]
        - Variable references: install_requires = DEPS
        - setup_requires and extras_require
        - Multiline lists
        
        Args:
            content: Raw setup.py content
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        # Strategy 1: Find inline lists with better regex
        # Use [\s\S]*? to match across newlines until we find matching brackets
        inline_patterns = [
            r'install_requires\s*=\s*\[([\s\S]*?)\]',
            r'install_requires\s*=\s*\(["\']?([\s\S]*?)["\']?\)',
        ]
        
        for pattern in inline_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                deps = self._parse_requirements_list(match)
                for dep in deps:
                    parsed = self._parse_package_spec(dep)
                    if parsed:
                        dependencies.append(parsed)
        
        # Strategy 2: Find variable assignments (e.g., DEPS = ["pkg1", "pkg2"])
        # Look for patterns like: VARIABLE = [...]
        # Use greedy matching to capture full list content
        var_pattern = r'(\w+)\s*=\s*\[(.*?)\]'
        
        var_map = {}
        for match in re.finditer(var_pattern, content, re.DOTALL):
            var_name = match.group(1)
            var_content = match.group(2)
            deps = self._parse_requirements_list(var_content)
            var_map[var_name] = deps
        
        # Find references to these variables (case-insensitive)
        ref_patterns = [
            r'install_requires\s*=\s*(\w+)',
            r'setup_requires\s*=\s*(\w+)',
        ]
        
        for ref_pattern in ref_patterns:
            for match in re.finditer(ref_pattern, content, re.IGNORECASE):
                var_name = match.group(1)
                if var_name in var_map:
                    for dep in var_map[var_name]:
                        parsed = self._parse_package_spec(dep)
                        if parsed:
                            dependencies.append(parsed)
        
        # Strategy 3: Parse extras_require
        extras_pattern = r'extras_require\s*=\s*\{([^}]+)\}'
        for match in re.finditer(extras_pattern, content):
            extras_block = match.group(1)
            # Find all key: value pairs or key = value pairs
            for extra_match in re.finditer(r'["\']?(\w+)["\']?\s*[:=]\s*\[([\s\S]*?)\]', extras_block):
                extra_deps = self._parse_requirements_list(extra_match.group(2))
                for dep in extra_deps:
                    parsed = self._parse_package_spec(dep)
                    if parsed:
                        dependencies.append(parsed)
        
        return dependencies
    
    def _parse_package_json_string(self, content: str) -> List[Dict[str, Any]]:
        """Parse a package.json string.
        
        Args:
            content: Raw package.json content
            
        Returns:
            List of dependencies
        """
        dependencies = []
        
        try:
            data = json.loads(content)
            
            # Parse both dependencies and devDependencies
            for key in ['dependencies', 'devDependencies', 'peerDependencies']:
                deps_dict = data.get(key, {})
                for name, version in deps_dict.items():
                    dependencies.append({
                        'name': name,
                        'version': self._normalize_version(version),
                    })
        except json.JSONDecodeError:
            pass
        
        return dependencies
    
    def _normalize_version(self, version: str) -> str:
        """Normalize a version string.
        
        Args:
            version: Version string (e.g., ^1.0.0, ~1.0.0, >=1.0.0)
            
        Returns:
            Normalized version string
        """
        if not version:
            return None
        if version.startswith('^'):
            return version[1:]
        elif version.startswith('~'):
            return version[1:]
        elif version.startswith('>='):
            return version[2:]
        elif version.startswith('<='):
            return version[2:]
        elif version.startswith('>'):
            return version[1:]
        elif version.startswith('<'):
            return version[1:]
        elif version.startswith('='):
            return version[1:]
        else:
            return version