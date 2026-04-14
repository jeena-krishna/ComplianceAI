# ComplianceAI

An open source tool that scans a project's dependency files, analyzes licenses, detects conflicts, and generates compliance reports.

## Features

- Scans dependency files (requirements.txt, package.json, etc.)
- Resolves dependencies and their sub-dependencies
- Identifies license types for each dependency
- Detects license conflicts
- Generates clear compliance reports
- Uses multiple AI agents coordinated by an orchestrator

## Architecture

- **Orchestrator**: Coordinates the workflow between agents
- **Dependency Agent**: Scans and resolves project dependencies
- **License Agent**: Identifies licenses for each dependency
- **Conflict Agent**: Detects license conflicts between dependencies
- **Report Agent**: Generates human-readable compliance reports

## Installation

```bash
pip install complianceai
```

## Usage

```bash
complianceai scan /path/to/project
```

## Development

This project follows a modular architecture with separate agents handling specific responsibilities.