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
        
        # Apache variants
        'apache': 'Apache-2.0',
        'apache-2.0': 'Apache-2.0',
        'apache2': 'Apache-2.0',
        'apache license 2.0': 'Apache-2.0',
        'apache license, version 2.0': 'Apache-2.0',
        'apache 2.0': 'Apache-2.0',
        
        # GPL variants
        'gpl': 'GPL-3.0',
        'gpl-3.0': 'GPL-3.0',
        'gpl3': 'GPL-3.0',
        'gnu general public license v3 (gpl-3.0)': 'GPL-3.0',
        'gpl-2.0': 'GPL-2.0',
        'gpl2': 'GPL-2.0',
        
        # BSD variants
        'bsd': 'BSD-3-Clause',
        'bsd-3-clause': 'BSD-3-Clause',
        'bsd3': 'BSD-3-Clause',
        'bsd-2-clause': 'BSD-2-Clause',
        'bsd2': 'BSD-2-Clause',
        'simplified bsd': 'BSD-2-Clause',
        
        # ISC variants
        'isc': 'ISC',
        
        # MPL variants
        'mpl': 'MPL-2.0',
        'mpl-2.0': 'MPL-2.0',
        'mozilla public license 2.0': 'MPL-2.0',
        
        # Python specific
        'python software foundation license': 'PSF-2.0',
        'psf': 'PSF-2.0',
        
        # Creative Commons
        'cc0': 'CC0-1.0',
        'cc-by': 'CC-BY-4.0',
        'cc-by-sa': 'CC-BY-SA-4.0',
        
        # Public Domain
        'public domain': 'CC0-1.0',
        'unlicense': 'Unlicense',
        
        # AGPL
        'agpl-3.0': 'AGPL-3.0',
        'agpl': 'AGPL-3.0',
        
        # LGPL
        'lgpl-2.1': 'LGPL-2.1',
        'lgpl': 'LGPL-2.1',
        'lgpl-3.0': 'LGPL-3.0',
        
        # zlib
        'zlib': 'Zlib',
        
        # curl
        'curl': 'curl',
    }
    
    # License aliases that need case-insensitive matching
    COMMON_LICENSE_ALIASES = {
        # Various MIT aliases
        'the mit license': 'MIT',
        'mit license, version 2.0': 'MIT',
        
        # Various BSD aliases
        'new bsd': 'BSD-3-Clause',
        'three-clause bsd': 'BSD-3-Clause',
        
        # Various Apache aliases
        'apache license': 'Apache-2.0',
        
        # ISC
        'internet systems consortium, inc.': 'ISC',
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
    
    def identify_licenses(self, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify licenses for each dependency.
        
        Args:
            dependencies: List of dictionaries with dependency information (from crawler)
            
        Returns:
            List of dictionaries with normalized license information added
        """
        licensed_dependencies = []
        
        for dep in dependencies:
            name = dep.get('name', '')
            existing_license = dep.get('license')
            
            # Normalize the license
            normalized_license = self._normalize_license(existing_license)
            
            # Create the output with license information
            licensed_dep = {
                'name': name,
                'version': dep.get('version'),
                'license': normalized_license,
                'license_source': self._get_license_source(existing_license, normalized_license),
                'original_license': existing_license,  # Keep original for reference
            }
            
            licensed_dependencies.append(licensed_dep)
        
        return licensed_dependencies
    
    def _normalize_license(self, license_str: str) -> str:
        """Normalize a license string to standard SPDX identifier.
        
        Args:
            license_str: The license string to normalize
            
        Returns:
            Normalized SPDX license identifier or 'Unknown'
        """
        if not license_str:
            return 'Unknown'
        
        # Convert to string if not already
        license_str = str(license_str).strip()
        
        # If it's already a valid SPDX identifier, return it
        if license_str in ['MIT', 'Apache-2.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause', 
                          'BSD-2-Clause', 'ISC', 'MPL-2.0', 'LGPL-2.1', 'LGPL-3.0',
                          'AGPL-3.0', 'Zlib', 'PSF-2.0', 'Unlicense', 'CC0-1.0',
                          'CC-BY-4.0', 'CC-BY-SA-4.0']:
            return license_str
        
        # Try to look up the license in our mapping
        license_lower = license_str.lower()
        
        # Check for direct matches
        if license_lower in self._license_lookup:
            return self._license_lookup[license_lower]
        
        # Try to find partial matches
        for key, spdx_id in self._license_lookup.items():
            if key in license_lower or license_lower in key:
                return spdx_id
        
        # Try to extract SPDX from common patterns
        spdx_match = self._extract_spdx(license_str)
        if spdx_match:
            return spdx_match
        
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