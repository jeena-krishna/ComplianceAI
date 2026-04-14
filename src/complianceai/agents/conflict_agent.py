"""Conflict Agent - Detects license conflicts between dependencies."""

from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict


class ConflictAgent:
    """Agent responsible for detecting license conflicts."""
    
    # License categories for compatibility analysis
    LICENSE_CATEGORIES = {
        # Permissive licenses - allow most uses
        'permissive': ['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'Zlib', 'Unlicense'],
        
        # Copyleft - requires derivative works to use same license
        'copyleft': ['GPL-2.0', 'GPL-3.0', 'LGPL-2.1', 'LGPL-3.0'],
        
        # Strong copyleft - requires proprietary linking
        'strong_copyleft': ['AGPL-3.0'],
        
        # Weak copyleft - allows dynamic linking
        'weak_copyleft': ['LGPL-2.1', 'LGPL-3.0'],
        
        # Proprietary compatible
        'proprietary': ['CC0-1.0', 'Public Domain'],
        
        # OSI approved but with restrictions
        'restricted': ['MPL-2.0', 'PSF-2.0'],
        
        # Unknown
        'unknown': ['Unknown'],
    }
    
    # License compatibility matrix
    # Values: 'compatible', 'weak_compatible', 'incompatible', 'unknown'
    LICENSE_COMPATIBILITY = {
        # MIT is compatible with everything
        'MIT': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'BSD-3-Clause': 'compatible',
            'BSD-2-Clause': 'compatible',
            'ISC': 'compatible',
            'Zlib': 'compatible',
            'Unlicense': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'LGPL-2.1': 'compatible',
            'LGPL-3.0': 'compatible',
            'AGPL-3.0': 'compatible',
            'MPL-2.0': 'compatible',
            'PSF-2.0': 'compatible',
            'CC0-1.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # Apache-2.0 is permissive
        'Apache-2.0': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'BSD-3-Clause': 'compatible',
            'BSD-2-Clause': 'compatible',
            'ISC': 'compatible',
            'Zlib': 'compatible',
            'Unlicense': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'LGPL-2.1': 'compatible',
            'LGPL-3.0': 'compatible',
            'AGPL-3.0': 'compatible',
            'MPL-2.0': 'compatible',
            'PSF-2.0': 'compatible',
            'CC0-1.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # BSD variants
        'BSD-3-Clause': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'BSD-3-Clause': 'compatible',
            'BSD-2-Clause': 'compatible',
            'ISC': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # ISC
        'ISC': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'BSD-3-Clause': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # GPL-3.0 - strong copyleft
        'GPL-3.0': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'BSD-3-Clause': 'compatible',
            'ISC': 'compatible',
            'Zlib': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'LGPL-2.1': 'compatible',
            'LGPL-3.0': 'compatible',
            'AGPL-3.0': 'compatible',
            'MPL-2.0': 'compatible',
            'PSF-2.0': 'compatible',
            'CC0-1.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # GPL-2.0 - similar to GPL-3.0
        'GPL-2.0': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'LGPL-2.1': 'compatible',
            'Unknown': 'unknown',
        },
        
        # LGPL - weak copyleft
        'LGPL-2.1': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'GPL-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'LGPL-2.1': 'compatible',
            'LGPL-3.0': 'weak_compatible',
            'Unknown': 'unknown',
        },
        
        # AGPL - strong copyleft
        'AGPL-3.0': {
            'MIT': 'compatible',
            'Apache-2.0': 'weak_compatible',
            'GPL-3.0': 'weak_compatible',
            'AGPL-3.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # MPL-2.0 - restricted
        'MPL-2.0': {
            'MIT': 'compatible',
            'Apache-2.0': 'compatible',
            'GPL-3.0': 'compatible',
            'Unknown': 'unknown',
        },
        
        # Unknown license - can't determine compatibility
        'Unknown': {
            'MIT': 'unknown',
            'Apache-2.0': 'unknown',
            'GPL-3.0': 'unknown',
            'Unknown': 'unknown',
        },
    }
    
    # Conflict severity levels
    SEVERITY_LEVELS = {
        'critical': {
            'description': 'Critical conflict - licenses are incompatible',
            'action_required': 'Must resolve before using'
        },
        'warning': {
            'description': 'Warning - compatibility is uncertain or requires attribution',
            'action_required': 'Review license terms and add attribution if required'
        },
        'info': {
            'description': 'Info - potential compatibility issue',
            'action_required': 'No action required but be aware'
        },
    }
    
    # License conflicts that require attention
    SPECIFIC_CONFLICTS = [
        # (license1, license2, severity, reason)
        ('GPL-3.0', 'Proprietary', 'critical', 'GPL-3.0 is incompatible with proprietary use'),
        ('AGPL-3.0', 'Proprietary', 'critical', 'AGPL-3.0 is incompatible with proprietary use'),
        ('GPL-2.0', 'Proprietary', 'critical', 'GPL-2.0 is incompatible with proprietary use'),
    ]
    
    def __init__(self):
        """Initialize the Conflict Agent."""
        # Build reverse lookup for license categories
        self._license_to_category = {}
        for category, licenses in self.LICENSE_CATEGORIES.items():
            for license_str in licenses:
                self._license_to_category[license_str] = category
    
    def detect_conflicts(self, licensed_dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect license conflicts between dependencies.
        
        Args:
            licensed_dependencies: List of dictionaries with license info from LicenseAgent
            
        Returns:
            List of conflict dictionaries
        """
        conflicts = []
        
        if not licensed_dependencies:
            return conflicts
        
        # Group dependencies by license
        license_groups = defaultdict(list)
        for dep in licensed_dependencies:
            license = dep.get('license', 'Unknown')
            license_groups[license].append(dep)
        
        # Check for conflicts between different licenses
        licenses = list(license_groups.keys())
        
        # Check each pair of licenses for conflicts
        for i, lic1 in enumerate(licenses):
            for lic2 in licenses[i+1:]:
                # Get compatibility
                compatibility = self._check_compatibility(lic1, lic2)
                
                if compatibility != 'compatible':
                    # Find the conflicting packages
                    packages_with_lic1 = license_groups[lic1]
                    packages_with_lic2 = license_groups[lic2]
                    
                    # Create conflict entry
                    conflict = {
                        'severity': self._compatibility_to_severity(compatibility),
                        'license_1': lic1,
                        'license_2': lic2,
                        'compatibility': compatibility,
                        'packages_1': [p.get('name') for p in packages_with_lic1],
                        'packages_2': [p.get('name') for p in packages_with_lic2],
                        'description': self._get_conflict_description(lic1, lic2, compatibility),
                        'recommendation': self._get_recommendation(lic1, lic2, compatibility)
                    }
                    
                    conflicts.append(conflict)
        
        # Check for unknown licenses
        unknown_packages = [dep for dep in licensed_dependencies 
                          if dep.get('license') == 'Unknown' or not dep.get('license')]
        
        if unknown_packages:
            conflicts.append({
                'severity': 'warning',
                'license_1': 'Unknown',
                'license_2': 'Multiple',
                'compatibility': 'unknown',
                'packages': [p.get('name') for p in unknown_packages],
                'description': f'{len(unknown_packages)} packages have unknown licenses',
                'recommendation': 'Verify license information manually for each package'
            })
        
        return conflicts
    
    def _check_compatibility(self, license1: str, license2: str) -> str:
        """Check compatibility between two licenses.
        
        Args:
            license1: First license
            license2: Second license
            
        Returns:
            'compatible', 'weak_compatible', 'incompatible', or 'unknown'
        """
        # Same license is always compatible
        if license1 == license2:
            return 'compatible'
        
        # Check the compatibility matrix
        if license1 in self.LICENSE_COMPATIBILITY:
            if license2 in self.LICENSE_COMPATIBILITY[license1]:
                return self.LICENSE_COMPATIBILITY[license1][license2]
        
        # Try the reverse
        if license2 in self.LICENSE_COMPATIBILITY:
            if license1 in self.LICENSE_COMPATIBILITY[license2]:
                return self.LICENSE_COMPATIBILITY[license2][license1]
        
        # Default to unknown
        return 'unknown'
    
    def _compatibility_to_severity(self, compatibility: str) -> str:
        """Convert compatibility status to severity level.
        
        Args:
            compatibility: One of 'compatible', 'weak_compatible', 'incompatible', 'unknown'
            
        Returns:
            Severity level: 'critical', 'warning', or 'info'
        """
        if compatibility == 'incompatible':
            return 'critical'
        elif compatibility == 'weak_compatible':
            return 'warning'
        elif compatibility == 'unknown':
            return 'warning'
        else:
            return 'info'
    
    def _get_conflict_description(self, license1: str, license2: str, compatibility: str) -> str:
        """Get a description of the conflict.
        
        Args:
            license1: First license
            license2: Second license
            compatibility: Compatibility status
            
        Returns:
            Human-readable description
        """
        if compatibility == 'incompatible':
            return f'{license1} is incompatible with {license2}'
        elif compatibility == 'weak_compatible':
            return f'{license1} may have compatibility issues with {license2}'
        elif compatibility == 'unknown':
            return f'Compatibility between {license1} and {license2} is unknown'
        else:
            return 'No conflict detected'
    
    def _get_recommendation(self, license1: str, license2: str, compatibility: str) -> str:
        """Get recommendation for resolving the conflict.
        
        Args:
            license1: First license
            license2: Second license
            compatibility: Compatibility status
            
        Returns:
            Recommendation string
        """
        if compatibility == 'incompatible':
            return f'Replace either {license1} or {license2} with a compatible alternative'
        elif compatibility == 'weak_compatible':
            return f'Review license terms carefully - may require dynamic linking only'
        elif compatibility == 'unknown':
            return 'Verify license compatibility manually'
        else:
            return 'No action required'
    
    def get_license_category(self, license: str) -> str:
        """Get the category of a license.
        
        Args:
            license: License string
            
        Returns:
            Category string
        """
        return self._license_to_category.get(license, 'unknown')
    
    def is_proprietary_compatible(self, license: str) -> bool:
        """Check if a license is compatible with proprietary use.
        
        Args:
            license: License string
            
        Returns:
            True if compatible with proprietary use
        """
        category = self.get_license_category(license)
        return category in ['permissive', 'proprietary', 'weak_copyleft']