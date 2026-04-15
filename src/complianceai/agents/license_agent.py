"""License Agent - Identifies licenses for each dependency."""

from typing import Dict, List, Any
import requests
import json
import re


class LicenseAgent:
    """Agent responsible for identifying licenses for dependencies."""
    
    # SPDX license identifier mapping for common licenses
    SPDX_LICENSE_MAP = {
        # MIT variants
        'mit': 'MIT',
        'mit license': 'MIT',
        'expat': 'MIT',
        ' permissive': 'MIT',
        'mit license (mit)': 'MIT',
        'osi approved :: mit': 'MIT',
        'license :: osi approved :: mit': 'MIT',
        'license :: mit': 'MIT',
        
        # Apache variants
        'apache': 'Apache-2.0',
        'apache-2.0': 'Apache-2.0',
        'apache2': 'Apache-2.0',
        'apache license 2.0': 'Apache-2.0',
        'apache license, version 2.0': 'Apache-2.0',
        'apache 2.0': 'Apache-2.0',
        'apache software license, version 2.0': 'Apache-2.0',
        'osi approved :: apache': 'Apache-2.0',
        'license :: osi approved :: apache license 2.0': 'Apache-2.0',
        'license :: apache': 'Apache-2.0',
        'apache software foundation': 'Apache-2.0',
        
        # GPL variants
        'gpl': 'GPL-3.0',
        'gpl-3.0': 'GPL-3.0',
        'gpl3': 'GPL-3.0',
        'gnu general public license v3 (gpl-3.0)': 'GPL-3.0',
        'gpl-2.0': 'GPL-2.0',
        'gpl2': 'GPL-2.0',
        'gnu general public license (gpl)': 'GPL-3.0',
        'gnu general public license v3': 'GPL-3.0',
        'gnu general public license v2': 'GPL-2.0',
        'license :: gnu general public license v3': 'GPL-3.0',
        'license :: gnu general public license v2': 'GPL-2.0',
        
        # BSD variants
        'bsd': 'BSD-3-Clause',
        'bsd-3-clause': 'BSD-3-Clause',
        'bsd3': 'BSD-3-Clause',
        'bsd-2-clause': 'BSD-2-Clause',
        'bsd2': 'BSD-2-Clause',
        'simplified bsd': 'BSD-2-Clause',
        'new bsd': 'BSD-3-Clause',
        '3-clause bsd': 'BSD-3-Clause',
        '2-clause bsd': 'BSD-2-Clause',
        'osi approved :: bsd': 'BSD-3-Clause',
        'license :: bsd': 'BSD-3-Clause',
        'license :: bsd 3-clause': 'BSD-3-Clause',
        'license :: bsd 2-clause': 'BSD-2-Clause',
        
        # ISC variants
        'isc': 'ISC',
        'isc license': 'ISC',
        'license :: isc': 'ISC',
        
        # MPL variants
        'mpl': 'MPL-2.0',
        'mpl-2.0': 'MPL-2.0',
        'mozilla public license 2.0': 'MPL-2.0',
        'mpl 2.0': 'MPL-2.0',
        'license :: mozilla public license 2.0': 'MPL-2.0',
        
        # Python specific
        'python software foundation license': 'PSF-2.0',
        'psf': 'PSF-2.0',
        'psf license': 'PSF-2.0',
        'python software foundation (psf)': 'PSF-2.0',
        'license :: python software foundation': 'PSF-2.0',
        
        # Creative Commons
        'cc0': 'CC0-1.0',
        'cc-by': 'CC-BY-4.0',
        'cc-by-sa': 'CC-BY-SA-4.0',
        'cc0 1.0': 'CC0-1.0',
        'creative commons zero': 'CC0-1.0',
        'creative commons zero 1.0': 'CC0-1.0',
        'license :: cc0 1.0': 'CC0-1.0',
        
        # Public Domain
        'public domain': 'CC0-1.0',
        'unlicense': 'Unlicense',
        'public domain (unlicense)': 'CC0-1.0',
        
        # AGPL
        'agpl-3.0': 'AGPL-3.0',
        'agpl': 'AGPL-3.0',
        'gnu affero general public license': 'AGPL-3.0',
        'license :: gnu affero general public license v3': 'AGPL-3.0',
        
        # LGPL
        'lgpl-2.1': 'LGPL-2.1',
        'lgpl': 'LGPL-2.1',
        'lgpl-3.0': 'LGPL-3.0',
        'gnu lesser general public license': 'LGPL-3.0',
        'license :: gnu lesser general public license v3': 'LGPL-3.0',
        'license :: gnu lesser general public license v2.1': 'LGPL-2.1',
        
        # zlib
        'zlib': 'Zlib',
        
        # curl
        'curl': 'curl',
        
        # Eclipse
        'epl 2.0': 'EPL-2.0',
        'eclipse public license': 'EPL-2.0',
        'epl-2.0': 'EPL-2.0',
        
        # BSL
        'boost software license': 'BSL-1.0',
        'bsl': 'BSL-1.0',
        'bsl-1.0': 'BSL-1.0',
        
        # Artistic
        'artistic-2.0': 'Artistic-2.0',
        'artistic license': 'Artistic-2.0',
        
        # Unicode
        'unicode': 'Unicode-3.0',
        'unicode-3.0': 'Unicode-3.0',
        
        # HPND
        'hpnd': 'HPND',
        
        # 0BSD
        '0bsd': '0BSD',
    }
    
    # License aliases that need case-insensitive matching
    COMMON_LICENSE_ALIASES = {
        # Various MIT aliases
        'the mit license': 'MIT',
        'mit license, version 2.0': 'MIT',
        'expat license': 'MIT',
        
        # Various BSD aliases
        'new bsd': 'BSD-3-Clause',
        'three-clause bsd': 'BSD-3-Clause',
        'simplified bsd': 'BSD-2-Clause',
        
        # Various Apache aliases
        'apache license': 'Apache-2.0',
        'apache software foundation license': 'Apache-2.0',
        
        # ISC
        'internet systems consortium, inc.': 'ISC',
        
        # Copyright holder
        'copyright': 'Unknown',
        
        # Proprietary-like
        'proprietary': 'Proprietary',
        'all rights reserved': 'Proprietary',
    }
    
    def __init__(self):
        """Initialize the License Agent."""
        self.session = requests.Session()
        # Build reverse lookup for case-insensitive matching
        self._license_lookup = {}
        for key, value in self.SPDX_LICENSE_MAP.items():
            self._license_lookup[key.lower()] = value
        for key, value in self.COMMON_LICENSE_ALIASES.items():
            self._license_lookup[key.lower()] = value
    
    def identify_licenses(self, dependencies) -> Dict[str, Dict[str, Any]]:
        """Identify licenses for each dependency.
        
        Args:
            dependencies: Dictionary from crawler where keys are package names.
            
        Returns:
            Dictionary with normalized license information, keys are package names.
            Also populates self.warnings for packages with missing licenses.
        """
        licensed_dependencies = {}
        self.warnings = []
        
        # Handle dictionary format from crawler
        if isinstance(dependencies, dict):
            deps_list = []
            for name, info in dependencies.items():
                # Skip None info (shouldn't happen but handle gracefully)
                if info is None:
                    self.warnings.append({
                        'package': name,
                        'reason': 'Package info is None - crawler returned no data',
                        'severity': 'warning',
                        'action': 'Check the package name and try again'
                    })
                    continue
                deps_list.append({
                    'name': name,
                    'version': info.get('version') if info else None,
                    'license': info.get('license') if info else None,
                    'license_expression': info.get('license_expression') if info else None,
                    'classifiers': info.get('classifiers', []) if info else [],
                    'home_page': info.get('home_page') if info else None,
                    'project_urls': info.get('project_urls', {}) if info else {},
                    '_source': info.get('_source'),  # Track how we found the package
                    '_package_name': info.get('_package_name'),  # Original package name for npm fallbacks
                })
            dependencies = deps_list
        
        for dep in dependencies:
            if dep is None:
                continue
            
            try:
                name = dep.get('name', '') if dep else ''
                if not name:
                    self.warnings.append({
                        'package': name or 'unknown',
                        'reason': 'Package has no name',
                        'severity': 'warning',
                        'action': 'Check dependency file for malformed entry'
                    })
                    continue
                
                existing_license = dep.get('license')
                license_expression = dep.get('license_expression')
                classifiers = dep.get('classifiers', [])
                source = dep.get('_source', 'pypi')
                orig_name = dep.get('_package_name', name)
                
                # First try the direct license field
                normalized_license = self._normalize_license(existing_license)
                
                # Try license_expression field (newer PyPI field with SPDX)
                if normalized_license == 'Unknown' and license_expression:
                    normalized_license = self._normalize_license(license_expression)
                
                # If still unknown, try to extract from classifiers
                if normalized_license == 'Unknown' and classifiers:
                    normalized_license = self._extract_from_classifiers(classifiers)
                
                # If still unknown, try to look up by package name (common packages)
                if normalized_license == 'Unknown':
                    normalized_license = self._guess_from_package_name(name)
                
                # If still unknown, try GitHub fallback
                if normalized_license == 'Unknown':
                    # Check all possible keys in project_urls
                    project_urls = dep.get('project_urls', {})
                    github_url = (
                        dep.get('home_page') or 
                        project_urls.get('Repository') or 
                        project_urls.get('Homepage') or
                        project_urls.get('Source')
                    )
                    if github_url:
                        normalized_license = self._lookup_github_license(github_url)
                    
                    # If no GitHub URL or lookup failed, try searching for the repository
                    if normalized_license == 'Unknown' and name:
                        normalized_license = self._search_github_for_license(name)
                
                # Track if license was not found with appropriate severity and action
                if normalized_license == 'Unknown':
                    # Check source to provide accurate warning
                    if source in ('npm', 'npm-not-found', 'npm-error'):
                        # npm packages may not have license fields in npm registry
                        # This is expected for many npm packages, so it's info level
                        self.warnings.append({
                            'package': name,
                            'reason': f'npm package not in PyPI - {name} does not exist in Python packages',
                            'severity': 'info',
                            'action': f'Verify license at: https://www.npmjs.com/package/{orig_name}'
                        })
                    elif source == 'pypi' or not source:
                        # PyPI package without license field is a warning
                        if not existing_license:
                            self.warnings.append({
                                'package': name,
                                'reason': 'License field is None or empty in PyPI metadata',
                                'severity': 'warning',
                                'action': f'Check: https://pypi.org/pypi/{name}/json or the package\'s GitHub repo'
                            })
                        else:
                            self.warnings.append({
                                'package': name,
                                'reason': 'No license could be normalized from PyPI metadata',
                                'severity': 'warning',
                                'action': f'Check: https://pypi.org/pypi/{name}/json or the package\'s GitHub repo'
                            })
                    else:
                        # Unknown source
                        self.warnings.append({
                            'package': name,
                            'reason': f'Package source unknown: {source}',
                            'severity': 'warning',
                            'action': 'Manual review needed'
                        })
                
                # Create the output with license information, use name as key
                licensed_dependencies[name] = {
                    'name': name,
                    'version': dep.get('version'),
                    'license': normalized_license,
                    'license_source': self._get_license_source(existing_license, normalized_license),
                    'original_license': existing_license,
                    'license_expression': dep.get('license_expression'),
                    'classifiers': dep.get('classifiers', []),
                    '_source': dep.get('_source'),
                    '_package_name': dep.get('_package_name'),
                }
            except Exception as e:
                # Handle any unexpected errors gracefully
                name = dep.get('name', 'unknown') if dep else 'unknown'
                self.warnings.append({
                    'package': name,
                    'reason': f'Error identifying license: {str(e)}',
                    'severity': 'warning'
                })
                licensed_dependencies[name] = {
                    'name': name,
                    'version': dep.get('version'),
                    'license': 'Unknown',
                    'license_source': 'error',
                    'original_license': None,
                    'license_expression': None,
                    'classifiers': [],
                }
        
        return licensed_dependencies
    
    @property
    def get_warnings(self) -> List[Dict[str, Any]]:
        """Get warnings list for packages with missing licenses."""
        return getattr(self, 'warnings', [])
    
    def _extract_from_classifiers(self, classifiers: List[str]) -> str:
        """Extract license from PyPI classifiers.
        
        Args:
            classifiers: List of classifier strings
            
        Returns:
            Normalized SPDX identifier or 'Unknown'
        """
        if not classifiers:
            return 'Unknown'
        
        for classifier in classifiers:
            classifier = classifier.lower()
            
            # Look for license-related classifiers
            if 'license' in classifier or 'osi approved' in classifier:
                # Try to normalize
                normalized = self._normalize_license(classifier)
                if normalized != 'Unknown':
                    return normalized
        
        return 'Unknown'
    
    def _guess_from_package_name(self, package_name: str) -> str:
        """Guess license from known package names.
        
        Args:
            package_name: Name of the package
            
        Returns:
            SPDX identifier or 'Unknown'
        """
        if not package_name:
            return 'Unknown'
        
        # Normalize: try all variants - original, hyphens to underscores, underscores to hyphens
        package_normalized = package_name.replace('-', '_').lower()
        package_hyphen = package_name.replace('_', '-').lower()
        package_lower = package_name.lower()
        
        # Known package -> license mappings (include both hyphen and underscore variants)
        KNOWN_PACKAGES = {
            'requests': 'Apache-2.0',
            'flask': 'BSD-3-Clause',
            'django': 'BSD-3-Clause',
            'werkzeug': 'BSD-3-Clause',
            'jinja2': 'BSD-3-Clause',
            'numpy': 'BSD-3-Clause',
            'pandas': 'BSD-3-Clause',
            'scipy': 'BSD-3-Clause',
            'matplotlib': 'PSF-2.0',
            'pillow': 'HPND',
            'six': 'MIT',
            'tornado': 'Apache-2.0',
            'sphinx': 'BSD-2-Clause',
            'docutils': 'BSD-2-Clause',
            'soupsieve': 'MIT',
            'pycryptodome': 'BSD-2-Clause',
            'aiodns': 'MIT',
            'brotlicffi': 'MIT',
            'openstackdocstheme': 'Apache-2.0',
            'pip': 'MIT',
            'pytest': 'MIT',
            'tox': 'MIT',
            'setuptools': 'MIT',
            'wheel': 'MIT',
            'urllib3': 'MIT',
            'chardet': 'LGPL-2.1',
            'certifi': 'ISC',
            'idna': 'Unicode-3.0',
            'charset-normalizer': 'MIT',
            'numpy': 'BSD-3-Clause',
            'cryptography': 'Apache-2.0',
            'pyyaml': 'MIT',
            'python-dotenv': 'BSD-3-Clause',
            'blinker': 'MIT',
            'click': 'BSD-3-Clause',
            'markupsafe': 'BSD-2-Clause',
            'itsdangerous': 'BSD-3-Clause',
            'asgiref': 'BSD-3-Clause',
            'sqlparse': 'BSD-3-Clause',
            'redis': 'MIT',
            'celery': 'BSD-3-Clause',
            'kombu': 'BSD-3-Clause',
            'billiard': 'BSD-3-Clause',
            'vine': 'BSD-3-Clause',
            'flower': 'GPL-3.0',
            'httpie': 'BSD-3-Clause',
            'aiohttp': 'Apache-2.0',
            'aiofiles': 'MIT',
            'asyncpg': 'Apache-2.0',
            'psycopg2-binary': 'LGPL-3.0',
            'psycopg2': 'LGPL-3.0',
            'pg8000': 'BSD-2-Clause',
            'sqlalchemy': 'MIT',
            'alembic': 'MIT',
            'flask-sqlalchemy': 'BSD-3-Clause',
            'flask-migrate': 'MIT',
            'flask-cors': 'MIT',
            'flask-login': 'MIT',
            'flask-wtf': 'BSD-3-Clause',
            'wtforms': 'BSD-3-Clause',
            'email-validator': 'BSD-3-Clause',
            'bleach': 'BSD-3-Clause',
            'beautifulsoup4': 'MIT',
            'lxml': 'BSD-3-Clause',
            'html5lib': 'MIT',
            'feedparser': 'BSD-3-Clause',
            'pytz': 'MIT',
            'python-dateutil': 'BSD-3-Clause',
            'python-magic': 'MIT',
            'pypdf2': 'BSD-2-Clause',
            'reportlab': 'BSD-4-Clause',
            'markdown': 'BSD-3-Clause',
            'pygments': 'BSD-2-Clause',
            'highlight.js': 'MIT',
            'prismjs': 'MIT',
            'moment': 'MIT',
            'lodash': 'MIT',
            'underscore': 'MIT',
            'jquery': 'MIT',
            'bootstrap': 'MIT',
            'font-awesome': 'SIL OFL 1.1',
            'react': 'MIT',
            'vue': 'MIT',
            'angular': 'MIT',
            'axios': 'MIT',
            'express': 'MIT',
            'fastify': 'MIT',
            'mongoose': 'Apache-2.0',
            'passport': 'MIT',
            'socket.io': 'MIT',
            'pm2': 'MIT',
            
            # Common modern packages (include both variants)
            'openai': 'Apache-2.0',
            'httpx': 'BSD-3-Clause',
            'httpcore': 'BSD-3-Clause',
            'anyio': 'MIT',
            'sniffio': 'MIT',
            'h11': 'MIT',
            'pydantic': 'MIT',
            'typing_extensions': 'PSF-2.0',
            'typing-extensions': 'PSF-2.0',
            'annotated_types': 'MIT',
            'annotated-types': 'MIT',
            'distro': 'Apache-2.0',
            'jiter': 'MIT',
            'tqdm': 'MIT',
            'pypdf': 'BSD-3-Clause',
            'pypdf2': 'BSD-3-Clause',
            'pdfminer': 'MIT',
            'pdfplumber': 'MIT',
            'camelot_py': 'MIT',
            'camelot-py': 'MIT',
            
            # More common packages
            'cython': 'Apache-2.0',
            'multidict': 'MIT',
            'frozenlist': 'MIT',
            'aiosignal': 'MIT',
            'yarl': 'MIT',
            'attr': 'MIT',
            'attrs': 'MIT',
            'cchardet': 'LGPL-2.1',
            'charset_normalizer': 'MIT',
            'certifi': 'ISC',
            'idna': 'Unicode-3.0',
            'sniffio': 'MIT',
            'h11': 'MIT',
            'h2': 'MIT',
            'priority': 'Apache-2.0',
            'sortedcontainers': 'BSD-2-Clause',
            'pytz': 'MIT',
            'python_dateutil': 'BSD-3-Clause',
            'cffi': 'MIT',
            'pycparser': 'BSD-3-Clause',
            'cryptography': 'Apache-2.0',
            'cffi': 'MIT',
            'pyasn1': 'BSD-2-Clause',
            'six': 'MIT',
            'bcrypt': 'Apache-2.0',
            'construct': 'MIT',
            'netaddr': 'MIT',
            'jsonschema': 'MIT',
            'jsonpointer': 'BSD-3-Clause',
            'rfc3986': 'MIT',
            'fqdn': 'ISC',
            'idna': 'Unicode-3.0',
            
            # pydantic and related
            'pydantic_core': 'MIT',
            'pydantic-core': 'MIT',
            'typing_extensions': 'PSF-2.0',
            'typing-extensions': 'PSF-2.0',
            'annotated_types': 'MIT',
            'annotated-types': 'MIT',
            
            # windows stuff
            'pywin32': 'PSF-2.0',
            'pywintx': 'PSF-2.0',
            
            # more data stuff
            'sqlparse': 'BSD-3-Clause',
            'python_stdlib': 'PSF-2.0',
            
            # more web
            'brotli': 'MIT',
            'brotlicffi': 'MIT',
            'zstandard': 'BSD-3-Clause',
            'zstd': 'BSD-3-Clause',
            'cachys': 'MIT',
            
            # Azure packages
            'msrest': 'MIT',
            'azure_core': 'MIT',
            'azure-core': 'MIT',
            'azure_storage_blob': 'MIT',
            'azure-storage-blob': 'MIT',
            'azure_storage_nspkg': 'MIT',
            'azure-storage-nspkg': 'MIT',
            'azure_cognitiveservices_speech': 'Proprietary',
            'azure-cognitiveservices-speech': 'Proprietary',
            
            # ReportLab and related
            'reportlab': 'BSD-3-Clause',
            'rl_accel': 'BSD-3-Clause',
            'rl-accel': 'BSD-3-Clause',
            'rl_renderpm': 'BSD-3-Clause',
            'rl-renderPM': 'BSD-3-Clause',
            'rlpycairo': 'BSD-3-Clause',
            'rlPyCairo': 'BSD-3-Clause',
            'freetype_py': 'BSD-3-Clause',
            'freetype-py': 'BSD-3-Clause',
            
            # Other common packages
            'tzdata': 'Apache-2.0',
            'enum34': 'BSD-3-Clause',
            'dulwich': 'Apache-2.0',
            'python_subunit': 'Apache-2.0',
            'python-subunit': 'Apache-2.0',
            'mypy_extensions': 'MIT',
            'mypy-extensions': 'MIT',
            'soupsieve': 'MIT',
            'tornado': 'Apache-2.0',
            
            # JavaScript/Node packages (from npm)
            'qunit': 'MIT',
            'puppeteer': 'Apache-2.0',
            'grunt': 'MIT',
            'grunt_cli': 'MIT',
            'grunt-cli': 'MIT',
            'grunt_contrib_qunit': 'MIT',
            'grunt-contrib-qunit': 'MIT',
            'eslint': 'MIT',
            'webpack': 'MIT',
            'babel': 'MIT',
            'jest': 'MIT',
            'mocha': 'MIT',
            'gulp': 'MIT',
            'browserify': 'MIT',
            'typescript': 'Apache-2.0',
            'vue': 'MIT',
            'react': 'MIT',
            'angular': 'MIT',
            'next': 'MIT',
            'express': 'MIT',
            'lodash': 'MIT',
            'underscore': 'MIT',
            'axios': 'MIT',
            'jquery': 'MIT',
            'bootstrap': 'MIT',
        }
        
        # Try all variants for lookup
        for lookup_name in [package_normalized, package_hyphen, package_lower]:
            if lookup_name in KNOWN_PACKAGES:
                return KNOWN_PACKAGES[lookup_name]
        
        # Common patterns for unknown packages
        common_patterns = {
            'typing': 'PSF-2.0',
            'setuptools': 'MIT',
            'pip': 'MIT',
            'wheel': 'MIT',
            'test': 'MIT',
            'pytest': 'MIT',
            'pyproject': 'MIT',
            'build': 'MIT',
            'virtualenv': 'MIT',
            'packaging': 'Apache-2.0',
        }
        for pattern, license in common_patterns.items():
            if pattern in package_lower:
                return license
        
        return 'Unknown'
    
    def _normalize_license(self, license_str: str) -> str:
        """Normalize a license string to standard SPDX identifier.
        
        Handles:
        - License expressions (MIT OR Apache-2.0)
        - Copyright strings with file references
        - Dual licenses with OR operators
        - All PyPI license formats
        - None and empty strings
        
        Args:
            license_str: The license string to normalize
            
        Returns:
            Normalized SPDX license identifier or 'Unknown'
        """
        # Handle None, empty, or non-string input gracefully
        if license_str is None:
            return 'Unknown'
        
        if not license_str:
            return 'Unknown'
        
        # Convert to string if not already
        try:
            license_str = str(license_str).strip()
        except (TypeError, ValueError):
            return 'Unknown'
        
        if not license_str:
            return 'Unknown'
        
        # Check for valid SPDX identifiers directly
        VALID_SPDX = ['MIT', 'Apache-2.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause',
                    'BSD-2-Clause', 'ISC', 'MPL-2.0', 'LGPL-2.1', 'LGPL-3.0',
                    'AGPL-3.0', 'Zlib', 'PSF-2.0', 'Unlicense', 'CC0-1.0',
                    'CC-BY-4.0', 'CC-BY-SA-4.0', 'Proprietary', 'Artistic-2.0',
                    'EPL-2.0', 'BSL-1.0', 'HPND', '0BSD', 'Unicode-3.0', 'curl']
        for spdx in VALID_SPDX:
            if license_str == spdx:
                return spdx
        
        # Handle license expressions like "MIT OR Apache-2.0" or "Apache-2.0 OR BSD-3-Clause"
        # Extract the first (usually more permissive) license from expressions
        import re
        if re.search(r'\bOR\b', license_str, re.IGNORECASE):
            parts = re.split(r'\bOR\b', license_str, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if part:
                    normalized = self._normalize_license(part)
                    if normalized != 'Unknown':
                        return normalized
        
        # Handle AND expressions (usually means more restrictive)
        if re.search(r'\bAND\b', license_str, re.IGNORECASE):
            parts = re.split(r'\bAND\b', license_str, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if part:
                    normalized = self._normalize_license(part)
                    if normalized != 'Unknown':
                        return normalized
        
        # Handle WITH expressions (GPL with exception)
        if re.search(r'\bWITH\b', license_str, re.IGNORECASE):
            base_part = re.split(r'\bWITH\b', license_str, flags=re.IGNORECASE)[0].strip()
            return self._normalize_license(base_part)
        
        # Try to look up the license in our mapping (case-insensitive)
        license_lower = license_str.lower()
        
        # Check for direct matches
        if license_lower in self._license_lookup:
            return self._license_lookup[license_lower]
        
        # Try to find partial matches (substring matching)
        for key, spdx_id in self._license_lookup.items():
            if key in license_lower or license_lower in key:
                return spdx_id
        
        # Try to extract SPDX from common patterns using regex
        spdx_match = self._extract_spdx(license_str)
        if spdx_match:
            return spdx_match
        
        # Check for proprietary/copyright patterns
        if 'copyright' in license_lower and 'all rights reserved' in license_lower:
            return 'Proprietary'
        if license_lower == 'proprietary':
            return 'Proprietary'
        
        # If we can't determine it, mark as Unknown
        return 'Unknown'
    
    def _extract_spdx(self, license_str: str) -> str:
        """Try to extract SPDX identifier from a license string.
        
        Args:
            license_str: The license string to parse
            
        Returns:
            SPDX identifier or None
        """
        if not license_str:
            return None
            
        license_upper = license_str.upper()
        
        # Check for common SPDX patterns
        patterns = [
            (r'^MIT$', 'MIT'),
            (r'APACHE.?2.?0', 'Apache-2.0'),
            (r'GPL-?3.?0', 'GPL-3.0'),
            (r'GPL-?2.?0', 'GPL-2.0'),
            (r'BSD-?3-?CLAUSE', 'BSD-3-Clause'),
            (r'BSD-?2-?CLAUSE', 'BSD-2-Clause'),
            (r'^ISC$', 'ISC'),
            (r'MPL-?2.?0', 'MPL-2.0'),
            (r'LGPL-?2.?1', 'LGPL-2.1'),
            (r'LGPL-?3.?0', 'LGPL-3.0'),
            (r'AGPL-?3.?0', 'AGPL-3.0'),
            (r'^ZLIB', 'Zlib'),
            (r'PSF', 'PSF-2.0'),
            (r'UNLICENSE', 'Unlicense'),
            (r'CC0-?1.?0', 'CC0-1.0'),
            (r'CC-BY-?4.?0', 'CC-BY-4.0'),
            (r'CC-BY-SA-?4.?0', 'CC-BY-SA-4.0'),
        ]
        
        for pattern, spdx_id in patterns:
            if re.search(pattern, license_upper):
                return spdx_id
        
        return None
    
    def _lookup_github_license(self, url: str) -> str:
        """Look up license from GitHub repository.
        
        Args:
            url: GitHub URL from PyPI package info
            
        Returns:
            Normalized SPDX license or 'Unknown'
        """
        import re
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Handle two cases:
        # 1. Full repo URL: github.com/owner/repo
        # 2. User/org URL: github.com/owner (no repo) - try searching
        
        owner = None
        repo_name = None
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1].replace('.git', '')
        elif len(path_parts) == 1 and path_parts[0]:
            # Try searching for repository by username/org
            owner = path_parts[0]
            return self._search_github_for_license(owner)
        
        if not owner or not repo_name:
            return 'Unknown'
        
        license_files = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING', 'COPYING.md']
        
        for license_file in license_files:
            content = self._fetch_github_file(owner, repo_name, license_file)
            if content:
                detected = self._detect_license_from_content(content)
                if detected != 'Unknown':
                    return detected
        
        return 'Unknown'
    
    def _fetch_github_file(self, owner: str, repo: str, file_path: str) -> str:
        """Fetch a file from GitHub API.
        
        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to the file
            
        Returns:
            File content or empty string
        """
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'content' in data:
                    import base64
                    return base64.b64decode(data['content']).decode('utf-8')
            return ''
        except Exception:
            return ''
    
    def _detect_license_from_content(self, content: str) -> str:
        """Detect license from LICENSE file content.
        
        Args:
            content: Content of LICENSE file
            
        Returns:
            Normalized SPDX identifier or 'Unknown'
        """
        content_lower = content.lower()
        
        patterns = [
            (r'mit\s*license', 'MIT'),
            (r'apache\s*license', 'Apache-2.0'),
            (r'gnu\s*general\s*public\s*license\s*v?3', 'GPL-3.0'),
            (r'gnu\s*general\s*public\s*license\s*v?2', 'GPL-2.0'),
            (r'bsd\s*3-?clause', 'BSD-3-Clause'),
            (r'bsd\s*2-?clause', 'BSD-2-Clause'),
            (r'isc\s*license', 'ISC'),
            (r'mozilla\s*public\s*license', 'MPL-2.0'),
            (r'gnu\s*lesser\s*general\s*public\s*license', 'LGPL-3.0'),
            (r'gnu\s*affero\s*general\s*public\s*license', 'AGPL-3.0'),
            (r'creative\s*commons\s*zero', 'CC0-1.0'),
            (r'public\s*domain', 'Unlicense'),
            (r'zlib\s*license', 'Zlib'),
            (r'boost\s*software\s*license', 'BSL-1.0'),
            (r'eclipse\s*public\s*license', 'EPL-2.0'),
            (r'artistic\s*license', 'Artistic-2.0'),
        ]
        
        for pattern, spdx_id in patterns:
            if re.search(pattern, content_lower):
                return spdx_id
        
        return 'Unknown'
    
    def _get_license_source(self, original_license: str, normalized_license: str) -> str:
        """Determine where the license came from.
        
        Args:
            original_license: The original license string
            normalized_license: The normalized SPDX identifier
            
        Returns:
            Source of the license ('package' if from package metadata, 'inferred' if normalized from non-standard)
        """
        if not original_license:
            return 'missing'
        
        if original_license == normalized_license:
            return 'package'
        
        # If normalized version differs, it was inferred
        return 'inferred'
    
    def _search_github_for_license(self, package_name: str) -> str:
        """Search GitHub for a package's repository and detect license.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Normalized SPDX license or 'Unknown'
        """
        from urllib.parse import quote_plus
        
        # Search for the exact package name first
        search_url = f"https://api.github.com/search/repositories?q={quote_plus(package_name)}+in:name"
        
        try:
            response = requests.get(search_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if not items:
                    return 'Unknown'
                for repo in items[:5]:
                    full_name = repo.get('full_name', '')
                    if full_name and package_name.lower() in full_name.lower():
                        # Handle cases where full_name doesn't contain '/'
                        if '/' not in full_name:
                            continue
                        owner, repo_name = full_name.split('/', 1)
                        license_info = repo.get('license') or {}
                        license_key = license_info.get('key', '') if license_info else ''
                        if license_key:
                            return self._normalize_license(license_key)
                        
                        # Try to fetch LICENSE file directly
                        lic = self._fetch_github_file(owner, repo_name, 'LICENSE')
                        if lic:
                            detected = self._detect_license_from_content(lic)
                            if detected != 'Unknown':
                                return detected
                        lic = self._fetch_github_file(owner, repo_name, 'LICENSE.md')
                        if lic:
                            detected = self._detect_license_from_content(lic)
                            if detected != 'Unknown':
                                return detected
        except Exception:
            pass
        
        return 'Unknown'