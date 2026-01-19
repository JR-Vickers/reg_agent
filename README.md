# Getting started
docker build -t reg-agent .
docker run -p 8000:8000 reg-agent

---

# Docker
Build the image:  
docker build -t reg-agent .

Start the container with environment variables:  
docker run -p 8000:8000 --env-file .env reg-agent

Start in background:  
docker run -d -p 8000:8000 --env-file .env reg-agent

Check running containers:  
docker ps

Stop a container:  
docker stop <container_id>

Stop all containers:  
docker stop $(docker ps -q)

Test the API:  
curl http://localhost:8000/health

Quick rebuild and run:  
docker build -t reg-agent . && docker run -p 8000:8000 --env-file .env reg-agent

---

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