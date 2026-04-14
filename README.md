# ComplianceAI

**Automated Dependency License Compliance Scanner**

An open source tool that scans project dependency files (requirements.txt, package.json), analyzes licenses, detects conflicts, and generates compliance reports using a multi-agent AI architecture.

## Why It Matters

Using open source dependencies with incompatible or conflicting licenses can lead to:

- **Legal risk**: License violations can result in lawsuits or forced code release
- **IP exposure**: Strong copyleft licenses (GPL) may require exposing your source code
- **Compliance failures**: Enterprise environments may reject packages with certain licenses
- **Audit failures**: Failed security/compliance audits during due diligence

ComplianceAI helps you proactively identify these issues before they become problems.

## Architecture

```
                    ┌─────────────────────┐
                    │       Input         │
                    │ (file / raw text)   │
                    └──────────┬──────────┘
                               │
                               v
                    ┌─────────────────────┐
                    │    Orchestrator     │
                    └──────────┬──────────┘
                               |
        ┌──────────┬──────────┼──────────┬──────────┐
        v          v          v          v          v
   ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
   │Dependency││License  ││Conflict ││Report   ││Dependency│
   │ Parser  ││Identifier││Analyzer ││Generator││ Crawler │
   │ Agent  ││ Agent   ││ Agent   ││ Agent   ││ Agent  │
   └─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
        ^          ^          ^          ^          ^
        └──────────┴──────────┴──────────┴──────────┘
                               │
                               v
                    ┌─────────────────────┐
                    │    Compliance      │
                    │       Report       │
                    └─────────────────────┘
```

### The 5 Agents

1. **Dependency Parser Agent** - Parses requirements.txt, package.json, or raw text; extracts package names and versions
2. **Dependency Crawler Agent** - Uses PyPI and npm APIs to resolve full dependency trees recursively
3. **License Identifier Agent** - Normalizes messy license names to SPDX identifiers; handles unknown licenses
4. **Conflict Analyzer Agent** - Detects license conflicts with severity levels (critical/warning/info)
5. **Report Generator Agent** - Creates summary, findings, and recommendations in text/JSON formats

**Orchestrator** - Wires all 5 agents together with error handling at each step

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Async HTTP | aiohttp |
| Vector Search | ChromaDB |
| Web UI | Streamlit |
| Testing | pytest |
| Package Manager | pip |

## Installation

### 1. Clone and Install

```bash
git clone https://github.com/jeena-krishna/ComplianceAI.git
cd ComplianceAI

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

On macOS/Linux with externally-managed environments, use:
```bash
pip install -r requirements.txt --break-system-packages
pip install -e . --break-system-packages
```

### 2. Verify Installation

```bash
python -c "from complianceai import Orchestrator; print('OK')"
```

## Usage

### CLI

```bash
# Analyze from file
complianceai scan requirements.txt

# Scan multiple files
complianceai scan requirements.txt package.json

# Output as JSON
complianceai scan --format json requirements.txt

# Set crawl depth
complianceai scan --depth 5 requirements.txt
```

### Streamlit Web UI

```bash
streamlit run src/complianceai/webui.py
```

Then open http://localhost:8501 in your browser.

## Example Output

### Input
```
numpy==1.24.0
pandas>=1.3.0
flask>=2.0.0
```

### CLI Report
```
================================================================================
                        COMPLIANCE REPORT
================================================================================

SUMMARY:
  Total Dependencies: 12
  Critical Issues: 1
  Warnings: 2
  Safe: 9

CRITICAL ISSUES:
  [⛔] GPL-2.0 vs Apache-2.0
      Package: numpy (MIT) vs tensorflow (Apache-2.0)
      Description: GPL-2.0 is incompatible with Apache-2.0 when combined
      Recommendation: Consider using alternative packages or upgrading TensorFlow

WARNINGS:
  [⚠️] License compatibility issue
      Package: scipy (BSD-3-Clause) vs matplotlib (MIT)
      Description: Minor license differences - review attribution

  [⚠️] Proprietary license detected
      Package: some-proprietary-client
      Description: All rights reserved - usage restrictions apply

SAFE:
  [✓] flask - MIT
  [✓] requests - Apache-2.0
  [✓] Jinja2 - BSD-3-Clause
```

### Web UI Screenshot
The Streamlit UI shows:
- Summary metrics at the top (color-coded)
- Critical issues in red with details
- Warnings in orange
- Complete dependency table with licenses

## Running Tests

```bash
# Run all tests
pytest

# Run agent tests only
pytest tests/agents/

# Run knowledge base tests
pytest tests/knowledge/

# Run with coverage
pytest --cov=src/complianceai --cov-report=html
```

## Project Structure

```
ComplianceAI/
├── README.md                 # This file
├── LICENSE                  # MIT License
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup
│
├── src/complianceai/       # Main package
│   ├── __init__.py        # Package init
│   ├── orchestrator.py    # Coordinates all agents
│   ├── cli.py             # Command-line interface
│   ├── webui.py           # Streamlit web UI
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── dependency_agent.py      # Dependency Parser
│   │   ├── dependency_crawler.py   # Dependency Crawler (async)
│   │   ├── license_agent.py        # License Identifier
│   │   ├── conflict_agent.py       # Compatibility Analyzer
│   │   └── report_agent.py          # Report Generator
│   │
│   ├── knowledge/                     # RAG knowledge base
│   │   ├── __init__.py
│   │   ├── license_data.py            # License metadata
│   │   └── rag.py                     # ChromaDB vectors
│   │
│   ├── config/           # Configuration files
│   ├── core/             # Core utilities
│   └── utils/            # Helper functions
│
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   │
│   ├── agents/
│   │   ├── test_dependency_agent.py
│   │   ├── test_dependency_crawler.py
│   │   ├── test_license_agent.py
│   │   ├── test_conflict_agent.py
│   │   └── test_report_agent.py
│   │
│   └── knowledge/
│       └── test_rag.py
│
└── chromadb_data/        # Created on first run
```

### Folder Explanations

| Folder | Purpose |
|--------|---------|
| `src/complianceai/` | Main source code |
| `src/complianceai/agents/` | 5 AI agent implementations |
| `src/complianceai/knowledge/` | License RAG with ChromaDB |
| `tests/` | Unit tests for all agents |
| `tests/agents/` | Individual agent tests |
| `tests/knowledge/` | RAG knowledge base tests |

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a PR.

## Acknowledgments

Built with a multi-agent architecture inspired by modern AI orchestration patterns.