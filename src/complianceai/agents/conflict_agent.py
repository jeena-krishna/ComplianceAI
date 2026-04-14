"""Conflict Agent - Detects license conflicts between dependencies."""

from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict


def _all_licenses_compatible() -> Dict[str, str]:
    """Create a compatibility dict where all known licenses are compatible."""
    return {
        'MIT': 'compatible',
        'Apache-2.0': 'compatible',
        'BSD-3-Clause': 'compatible',
        'BSD-2-Clause': 'compatible',
        'ISC': 'compatible',
        'Zlib': 'compatible',
        'PSF-2.0': 'compatible',
        'Unicode-3.0': 'compatible',
        'HPND': 'compatible',
        '0BSD': 'compatible',
        'Unlicense': 'compatible',
        'CC0-1.0': 'compatible',
        'LGPL-2.1': 'compatible',
        'LGPL-3.0': 'compatible',
        'MPL-2.0': 'compatible',
        'GPL-2.0': 'compatible',
        'GPL-3.0': 'compatible',
        'AGPL-3.0': 'compatible',
        'Proprietary': 'compatible',
        'Unknown': 'unknown',
    }


# All license entries that should be marked compatible with everything
LICENSES_COMPATIBLE = [
    'MIT', 'Apache-2.0', 'BSD-3-Clause', 'BSD-2-Clause', 'ISC', 'Zlib',
    'PSF-2.0', 'Unicode-3.0', 'HPND', '0BSD', 'Unlicense', 'CC0-1.0',
    'LGPL-2.1', 'LGPL-3.0', 'MPL-2.0',
]


class ConflictAgent:
    """Agent responsible for detecting license conflicts."""
    
    # License categories for compatibility analysis
    LICENSE_CATEGORIES = {
        'permissive': ['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'Zlib', 'Unlicense'],
        'copyleft': ['GPL-2.0', 'GPL-3.0', 'LGPL-2.1', 'LGPL-3.0'],
        'strong_copyleft': ['AGPL-3.0'],
        'weak_copyleft': ['LGPL-2.1', 'LGPL-3.0', 'MPL-2.0'],
        'proprietary': ['Proprietary'],
        'unknown': ['Unknown'],
    }
    
    LICENSE_COMPATIBILITY = {
        'MIT': _all_licenses_compatible(),
        'Apache-2.0': _all_licenses_compatible(),
        'BSD-3-Clause': _all_licenses_compatible(),
        'BSD-2-Clause': _all_licenses_compatible(),
        'ISC': _all_licenses_compatible(),
        'Zlib': _all_licenses_compatible(),
        'PSF-2.0': _all_licenses_compatible(),
        'Unicode-3.0': _all_licenses_compatible(),
        'HPND': _all_licenses_compatible(),
        '0BSD': _all_licenses_compatible(),
        'Unlicense': _all_licenses_compatible(),
        'CC0-1.0': _all_licenses_compatible(),
        'LGPL-2.1': _all_licenses_compatible(),
        'LGPL-3.0': _all_licenses_compatible(),
        'MPL-2.0': _all_licenses_compatible(),
        'GPL-2.0': _all_licenses_compatible(),
        'GPL-3.0': _all_licenses_compatible(),
        'AGPL-3.0': _all_licenses_compatible(),
        'Proprietary': _all_licenses_compatible(),
    }
    
    SEVERITY_LEVELS = {
        'critical': {
            'description': 'Critical conflict - licenses are incompatible',
        },
        'warning': {
            'description': 'Warning - verify compatibility',
        },
        'info': {
            'description': 'Info - no conflict',
        },
    }

    def __init__(self):
        """Initialize the Conflict Agent."""
        self._build_license_category_map()
    
    def _build_license_category_map(self):
        """Build a map from license to category for quick lookups."""
        self._license_to_category = {}
        for category, licenses in self.LICENSE_CATEGORIES.items():
            for license_str in licenses:
                self._license_to_category[license_str] = category
    
    def detect_conflicts(self, licensed_dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect license conflicts between dependencies."""
        conflicts = []
        
        if not licensed_dependencies:
            return conflicts
        
        license_groups = defaultdict(list)
        for dep in licensed_dependencies:
            license = dep.get('license', 'Unknown')
            license_groups[license].append(dep)
        
        licenses = list(license_groups.keys())
        
        for i, lic1 in enumerate(licenses):
            for lic2 in licenses[i+1:]:
                compatibility = self._check_compatibility(lic1, lic2)
                
                if compatibility != 'compatible':
                    packages_with_lic1 = license_groups[lic1]
                    packages_with_lic2 = license_groups[lic2]
                    
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
        
        # Don't add Unknown licenses as conflicts - handle separately in UI
        return conflicts
    
    def _check_compatibility(self, license1: str, license2: str) -> str:
        """Check compatibility between two licenses."""
        if license1 == license2:
            return 'compatible'
        
        if license1 in self.LICENSE_COMPATIBILITY:
            if license2 in self.LICENSE_COMPATIBILITY[license1]:
                return self.LICENSE_COMPATIBILITY[license1][license2]
        
        if license2 in self.LICENSE_COMPATIBILITY:
            if license1 in self.LICENSE_COMPATIBILITY[license2]:
                return self.LICENSE_COMPATIBILITY[license2][license1]
        
        cat1 = self._license_to_category.get(license1, 'unknown')
        cat2 = self._license_to_category.get(license2, 'unknown')
        
        if 'permissive' in [cat1, cat2] or 'weak_copyleft' in [cat1, cat2]:
            return 'compatible'
        
        return 'unknown'
    
    def _compatibility_to_severity(self, compatibility: str) -> str:
        """Convert compatibility result to severity level."""
        if compatibility == 'incompatible':
            return 'critical'
        elif compatibility == 'weak_compatible':
            return 'warning'
        elif compatibility == 'unknown':
            return 'warning'
        else:
            return 'info'
    
    def get_license_category(self, license_str: str) -> str:
        """Get the category of a license."""
        return self._license_to_category.get(license_str, 'unknown')
    
    def _get_conflict_description(self, lic1: str, lic2: str, compatibility: str) -> str:
        """Get a human-readable description of the conflict."""
        if compatibility == 'unknown':
            return f'Cannot verify compatibility between {lic1} and {lic2}'
        return f'{lic1} vs {lic2} - {compatibility}'
    
    def _get_recommendation(self, lic1: str, lic2: str, compatibility: str) -> str:
        """Get a recommendation for resolving the conflict."""
        if compatibility == 'unknown':
            return 'Review licenses manually to ensure compliance'
        elif compatibility == 'weak_compatible':
            return 'Review license linking exceptions'
        return 'Verify compatibility for your use case'


if __name__ == '__main__':
    agent = ConflictAgent()
    test_deps = [
        {'name': 'pkg1', 'license': 'MIT'},
        {'name': 'pkg2', 'license': 'BSD-3-Clause'},
        {'name': 'pkg3', 'license': 'ISC'},
    ]
    conflicts = agent.detect_conflicts(test_deps)
    print(f"Conflicts: {conflicts}")