"""Dependency Agent - Parses dependency files and extracts package information."""

import json
import os
import re
from typing import Dict, List, Any, Union
from urllib.parse import urlparse


class DependencyAgent:
    """Agent responsible for parsing dependency files and extracting package information."""
    
    def __init__(self):
        """Initialize the Dependency Agent."""
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
        
        # Remove whitespace
        spec = spec.strip()
        
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
        """Parse a GitHub URL by cloning and examining dependency files.
        
        Note: This is a simplified implementation. In production, you'd want to:
        1. Clone the repo (or use GitHub API)
        2. Look for dependency files
        3. Parse them
        4. Clean up
        """
        # For now, we'll return an empty list and note that this needs implementation
        # A real implementation would:
        # 1. Extract owner/repo from URL
        # 2. Use GitHub API to get contents
        # 3. Look for package.json, requirements.txt, etc.
        # 4. Download and parse those files
        return []