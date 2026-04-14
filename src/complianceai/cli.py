"""Command-line interface for ComplianceAI."""

import argparse
import sys
from .orchestrator import Orchestrator


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="ComplianceAI - Multi-agent license compliance analysis tool"
    )
    parser.add_argument(
        "command",
        choices=["scan"],
        help="Command to execute"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project to analyze (default: current directory)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)"
    )
    
    args = parser.parse_args()
    
    if args.command == "scan":
        orchestrator = Orchestrator()
        results = orchestrator.run_compliance_analysis(args.path)
        
        # TODO: Implement actual output formatting based on --format
        if args.format == "json":
            import json
            output = json.dumps(results, indent=2)
        else:
            # Simple text output for now
            output = f"""ComplianceAI Analysis Results
===========================
Project: {args.path}
Timestamp: {results.get('report', {}).get('timestamp', 'N/A')}
Total Dependencies: {results.get('report', {}).get('summary', {}).get('total_dependencies', 0)}
Total Conflicts: {results.get('report', {}).get('summary', {}).get('total_conflicts', 0)}
Risk Level: {results.get('report', {}).get('summary', {}).get('risk_level', 'UNKNOWN')}
"""
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())