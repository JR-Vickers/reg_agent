# Getting started
docker build -t reg-agent .
docker run -p 8000:8000 reg-agent

# Project Structure
src/
├── agents/           # Core agentic components
│   ├── orchestrator/ # Main coordination agent
│   ├── monitor/      # Regulatory source monitoring
│   ├── classify/     # Document classification
│   ├── assess/       # Gap analysis
│   └── route/        # Task routing and assignment
├── data/
│   ├── ingestion/    # Data source pipelines
│   ├── storage/      # Database models
│   └── models/       # Pydantic schemas
├── config/
│   ├── settings/     # Environment configuration
│   └── schemas/      # Validation schemas
└── utils/            # Shared utilities

tests/                # Test suites
├── unit/            # Unit tests per component
└── integration/     # End-to-end tests

docs/                # Documentation
infrastructure/      # Docker, deployment configs
scripts/            # Utility scripts